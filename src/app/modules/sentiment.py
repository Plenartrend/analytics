from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

from app.utils.config.settings import settings
from pipeline.pipeline.step import Step
from pipeline.types.result import Result, Ok
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse

from app.schema.schema import StanceResult, ClassifiedSpeech


class Sentiment(Step):
    def __init__(self, *, config: None):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech: ClassifiedSpeech = input_data.unwrap()

        parser = JsonOutputParser(pydantic_object=StanceResult)

        stance_prompt = PromptTemplate(
            template="""
        Evaluate the stance of the following text toward the topic "{topic}".

        Return a numerical value in the range [-1, 1]:

        GERMAN_STANCE_ANCHORS:
            +1.0: [
                "Ich stimme voll und ganz zu.",
                "Ich bin entschieden dafür.",
                "Ich unterstütze das ausdrücklich.",
                "Ich bejahe dies klar.",
            ],
            +0.5: [
                "Ich stimme zu.",
                "Ich bin dafür.",
                "Ich unterstütze das.",
                "Ich bin positiv eingestellt.",
            ],
            0.0: [
                "Ich bin neutral.",
                "Keine klare Position.",
                "Es ist irrelevant für mich."
            ],
            -0.5: [
                "Ich bin dagegen.",
                "Ich lehne es ab.",
                "Ich bin kritisch eingestellt.",
                "Ich bin negativ eingestellt."
            ],
            -1.0: [
                "Ich stimme entschieden nicht zu.",
                "Ich bin strikt dagegen.",
                "Ich verurteile dies.",
                "Ich lehne es völlig ab.",
            ]

        {format_instructions}

        Text:
        "{speech_text}"
        """,
            input_variables=["speech_text", "topic"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )

        llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=settings.DEEPSEEK_API_KEY,
            openai_api_base="https://api.deepseek.com",
            max_tokens=512,
            temperature=0,
        )

        stance_list = []

        for topic in speech.topics:
            prompt = stance_prompt.format_prompt(
                speech_text=speech.text,
                topic=topic
            ).to_messages()

            llm_result = llm.invoke(prompt)
            parsed: StanceResult = StanceResult(**parser.parse(llm_result.content))

            parsed.stance = max(min(parsed.stance, 1.0), -1.0)

            stance_list.append(parsed)

        return await pipeline_config.next(Ok({**speech.model_dump(), "sentiment": stance_list}), pipeline_config)
