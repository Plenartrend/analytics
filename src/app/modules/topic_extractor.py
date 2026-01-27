from typing import Any

from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pipeline.pipeline.step import Step
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from pipeline.types.result import Ok, Result

from ..schema.schema import TopicExtractorConfig, TopicForRequest
from ..utils.config.settings import settings


async def _execute_llm_call(prompt: list[BaseMessage], llm: ChatOpenAI, parser: JsonOutputParser) -> str:
    response = await llm.ainvoke(prompt)
    topic = parser.parse(response.content)["topic"]
    return topic


class TopicExtractor(Step):
    config: TopicExtractorConfig

    def __init__(self, *, config: TopicExtractorConfig):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        chunks = speech["chunks"]

        parser = JsonOutputParser(pydantic_object=TopicForRequest)
        prompt = PromptTemplate(
            template="Return the main topic of the following text in 1-3 words in German."
            "{query}\n"
            "{previous_topics}\n"
            "{format_instruction}",
            input_variables=["query", "previous_topics"],
            partial_variables={"format_instruction": parser.get_format_instructions()},
        )

        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=settings.DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
            max_tokens=1024,
            temperature=0,
        )

        topics = []

        if self.config.inject_topics is not None and len(self.config.inject_topics) > 0:
            for paper_title in self.config.inject_topics:
                prompt_for_inject = PromptTemplate(
                    template="Summarize the following document title in 1-3 words in German:"
                    "{query}\n"
                    "{format_instruction}\n",
                    input_variables=["query"],
                    partial_variables={"format_instruction": parser.get_format_instructions()},
                )
                formatted_prompt = prompt_for_inject.format_prompt(query=paper_title).to_messages()
                topics.append(await _execute_llm_call(formatted_prompt, llm, parser))

        for chunk in chunks:
            formatted_prompt = prompt.format_prompt(query=chunk, previous_topics=", ".join(topics)).to_messages()
            topics.append(await _execute_llm_call(formatted_prompt, llm, parser))

        return await pipeline_config.next(Ok({**speech, "topics": topics}), pipeline_config)
