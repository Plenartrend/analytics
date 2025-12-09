from typing import Any

from pipeline.pipeline.step import Step
from pipeline.types.result import Result, Ok
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.schema.schema import SpeechSplitterConfig


class SpeechSplitter(Step):
    def __init__(self, *, config: SpeechSplitterConfig):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        chunks = text_splitter.split_text(speech["text"])

        return await pipeline_config.next(Ok({**speech, "chunks": chunks}), pipeline_config)
