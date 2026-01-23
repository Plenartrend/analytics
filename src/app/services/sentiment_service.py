from pipeline.pipeline import Pipeline
from pipeline.schemas.schema import PipelineConfig
from pipeline.types import Ok

from ..modules.formatter import Formatter
from ..modules.sentiment import Sentiment
from ..schema.schema import (
    ClassifiedSpeech,
    FormatterConfig,
    SentimentClassifiedSpeech,
)


async def run_sentiment_analysis_pipeline(speeches: list[ClassifiedSpeech]) -> SentimentClassifiedSpeech:
    def formatter_final(speech: dict):
        scs = SentimentClassifiedSpeech(
            id=speech["id"],
            topics=speech["topics"],
            text=speech["text"],
            sentiment=speech["sentiment"],
        )

        return Ok(scs)

    pipeline = (
        Pipeline.init(input_data=speeches, pipeline_config=PipelineConfig(name="Sentiment Analysis Pipeline"))
        .exec(Sentiment(config=None))
        .exec(Formatter(config=FormatterConfig(formatter_function=formatter_final)))
        .compile()
    )

    return (await pipeline).unwrap()
