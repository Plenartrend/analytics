import inspect
from typing import Any

from pipeline.pipeline.step import Step
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from pipeline.types.result import Err, Result

from app.schema.schema import FormatterConfig


class Formatter(Step):
    def __init__(self, *, config: FormatterConfig):
        self.config = config

    async def run(
        self, input_data: Result[Any, Any], pipeline_config: PipelineModuleConfig
    ) -> PipelineResponse[Any, Any]:
        if input_data.is_err():
            return await pipeline_config.next(
                input_data,
                pipeline_config,
            )

        return_value: PipelineResponse = await pipeline_config.next(
            Err(
                f"Formatter function {self.config.formatter_function} "
                f"must accept 1 argument or 2 arguments with a provided store_key."
            ),
            pipeline_config,
        )

        if len(inspect.signature(self.config.formatter_function).parameters) == 1:
            return_value = await pipeline_config.next(
                self.config.formatter_function(input_data.unwrap()), pipeline_config
            )

        if len(inspect.signature(self.config.formatter_function).parameters) == 2 and self.config.store_key is not None:
            return_value = await pipeline_config.next(
                self.config.formatter_function(
                    input_data.unwrap(),
                    pipeline_config.cache[self.config.store_key].unwrap(),
                ),
                pipeline_config,
            )

        return return_value
