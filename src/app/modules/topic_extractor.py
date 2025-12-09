from typing import Any

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_openai import ChatOpenAI
from pipeline.pipeline.step import Step
from pipeline.types.result import Result, Ok
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from app.schema.schema import TopicForRequest
from app.utils.config.settings import settings

class TopicExtractor(Step):
    def __init__(self, *, config: None):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        chunks = speech["chunks"]

        parser = JsonOutputParser(pydantic_object=TopicForRequest)
        prompt = PromptTemplate(
            template="Return the main topic of the following text in 1-3 words in German. {format_instruction}\n{query}\n{previous_topics}",
            input_variables=["query", "previous_topics"],
            partial_variables={"format_instruction": parser.get_format_instructions()}
        )

        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=settings.DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
            max_tokens=1024,
            temperature=0,
        )

        topics = []
        for chunk in chunks:
            formatted_prompt = prompt.format_prompt(
                query=chunk,
                previous_topics=", ".join(topics)
            ).to_messages()
            response = llm.invoke(formatted_prompt)
            topic = parser.parse(response.content)["topic"]
            topics.append(topic)

        return await pipeline_config.next(Ok({**speech, "topics": topics}), pipeline_config)
