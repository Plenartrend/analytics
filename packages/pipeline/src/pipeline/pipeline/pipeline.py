from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable
from uuid import uuid4

from ..schemas import schema
from ..schemas.schema import PipelineConfig, PipelineModuleConfig, PipelineResponse
from ..types import Ok, Result
from .step import Step

LOGGER = logging.getLogger(__name__)


class SubPipeline:
    def __init__(self, functions: list[Callable] | None = None):
        self.functions = functions or []

    @staticmethod
    def init():
        return Pipeline(Ok(None), prevent_compilation=True)


class Pipeline:
    def __init__(
        self,
        input_data: Result[Any, Any],
        pipeline_config: PipelineConfig | None = None,
        functions: list[Callable] | None = None,
        prevent_compilation: bool = False,
    ):
        self.input_data = input_data
        self.config = pipeline_config
        self.functions = functions or []
        self.prevent_compilation = prevent_compilation

    @staticmethod
    def init(*, input_data: Any, pipeline_config: PipelineConfig) -> Pipeline:
        return Pipeline(Ok(input_data), pipeline_config)

    def exec(self, step: Step, *, iterations: int = 1) -> Pipeline:
        for _ in range(iterations):
            self.functions.append(step.run)
        return self

    def for_each(self, pipeline: Pipeline) -> Pipeline:
        async def seq_distributor(
            input_data: Result[Any, Any],
            pipeline_config: PipelineModuleConfig,
        ):
            if input_data.is_err():
                return await pipeline_config.next(
                    input_data,
                    pipeline_config,
                )

            results = []

            current_config = pipeline_config
            for requests in input_data.unwrap():
                resolved = await pipeline_config.next(
                    Ok(requests),
                    current_config,
                )

                results.append(resolved.data)
                current_config = resolved.pipeline_config

            return PipelineResponse(data=Ok(results), pipeline_config=current_config)

        async def sequential_compile_sub_pipeline(input_data, config):
            tmp_config = PipelineModuleConfig(**config.model_dump())
            del tmp_config.next

            result: PipelineResponse[Any, Any] = await Pipeline(
                input_data, tmp_config, [seq_distributor] + pipeline.functions
            )._compile()

            return await config.next(
                result.data,
                result.pipeline_config,
            )

        self.functions.append(sequential_compile_sub_pipeline)

        return self

    def parallel(self, pipeline: Pipeline):
        async def para_distributor(
            input_data: Result[Any, Any],
            pipeline_config: PipelineModuleConfig,
        ):
            if input_data.is_err():
                return await pipeline_config.next(
                    input_data,
                    pipeline_config,
                )

            promises = []

            for data in input_data.unwrap():
                promise = pipeline_config.next(
                    Ok(data),
                    pipeline_config,
                )
                promises.append(promise)

            results: list[PipelineResponse[Any, Any]] = await asyncio.gather(*promises)
            # Easy solution for now regarding the pipeline_config
            if len(results) == 0:
                return PipelineResponse(data=Ok([]), pipeline_config=pipeline_config)
            else:
                return PipelineResponse(
                    data=Ok([el.data for el in results]),
                    pipeline_config=results[0].pipeline_config,
                )

        async def parallel_compile_sub_pipeline(input_data, config):
            tmp_config = PipelineModuleConfig(**config.model_dump())
            del tmp_config.next

            result: PipelineResponse[Any, Any] = await Pipeline(
                input_data, tmp_config, [para_distributor] + pipeline.functions
            )._compile()

            # Easy solution for now...
            return await config.next(
                result.data,
                result.pipeline_config,
            )

        self.functions.append(parallel_compile_sub_pipeline)

        return self

    def do_while(
        self,
        *,
        body: Pipeline,
        condition: Callable[[Any, PipelineConfig], bool],
        after: Callable[
            [Result[Any, Any], Result[Any, Any], PipelineConfig], Result[Any, Any]
        ]
        | None = None,
    ):
        before_loop_value = str(uuid4())
        state = str(uuid4())

        async def do_while_compile_sub_pipeline(input_data, config):
            tmp_config = PipelineModuleConfig(**config.model_dump())
            del tmp_config.next

            result: PipelineResponse[Any, Any] = await Pipeline(
                input_data, tmp_config, body.functions
            )._compile()

            return await config.next(
                result.data,
                result.pipeline_config,
            )

        async def init_return_state(input_data, config: PipelineModuleConfig):
            config.cache[state] = []
            return await config.next(input_data, config)

        async def insert_into_state(input_data, config: PipelineModuleConfig):
            config.cache[before_loop_value] = input_data
            return await config.next(input_data, config)

        async def check_condition(
            input_data: Result[Any, Any], config: PipelineModuleConfig
        ):
            config.cache[state].append(input_data)

            if condition(input_data.unwrap(), config):
                config.next = functools.partial(
                    config.next.func,
                    [insert_into_state, do_while_compile_sub_pipeline, check_condition]
                    + config.next.args[0],
                )  # noqa
                if after is not None:
                    input_data = after(
                        input_data, config.cache[before_loop_value], config
                    )
                    config.cache.pop(before_loop_value)

                return await config.next(input_data, config)
            else:
                return await config.next(Ok(config.cache[state]), config)

        self.functions.append(init_return_state)
        self.functions.append(insert_into_state)
        self.functions.append(do_while_compile_sub_pipeline)
        self.functions.append(check_condition)

        return self

    async def _compile(self) -> PipelineResponse[Any, Any]:
        input_data = self.input_data

        if input_data is None:
            raise ValueError("No input data was provided")

        async def _next(
            functions, result, pipeline_config: PipelineModuleConfig
        ) -> PipelineResponse[Any, Any]:
            if len(functions) == 0:
                return schema.PipelineResponse(
                    data=result, pipeline_config=pipeline_config
                )
            current_function = functions[0]
            remaining_functions = functions[1:]
            new_pipeline_config = PipelineModuleConfig(**pipeline_config.model_dump())
            new_pipeline_config.next = functools.partial(_next, remaining_functions)
            return await current_function(result, new_pipeline_config)

        pmc = PipelineModuleConfig(
            **self.config.model_dump(), next=functools.partial(_next, self.functions)
        )

        return await pmc.next(input_data, pmc)

    async def compile(self) -> Result[Any, Any]:
        if self.prevent_compilation:
            raise ValueError("This Pipeline should not be compiled")
        LOGGER.info(
            f"Starting pipeline {self.config.name} with {len(self.functions)} steps"
        )
        return (await self._compile()).data
