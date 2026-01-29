from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pipeline.pipeline.step import Step
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from pipeline.types.result import Ok, Result

from ..schema.schema import SpeechSplitterConfig


class SpeechSplitter(Step):
    def __init__(self, *, config: SpeechSplitterConfig):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        chunk_size = self.config.chunk_size
        chunk_overlap = self.config.chunk_overlap

        if len(speech["text"]) > 50000:
            chunk_size = len(speech["text"]) / 2
            chunk_overlap = 0

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        chunks = text_splitter.split_text(speech["text"])

        return await pipeline_config.next(Ok({**speech, "chunks": chunks}), pipeline_config)
