from typing import Any

from pipeline.pipeline import Pipeline, SubPipeline
from pipeline.schemas.schema import PipelineConfig
from pipeline.types import Err, Ok, Result

from app.modules.formatter import Formatter
from app.modules.sentiment import Sentiment
from app.schema.schema import (
    ClassifiedSpeech,
    FormatterConfig,
    SentimentClassifiedSpeech,
)


async def run_sentiment_analysis_pipeline(speeches: list[ClassifiedSpeech]):
    def formatter_final(speeches: list[Result[dict, Any]]):
        res = []
        for speech in speeches:
            if speech.is_err():
                return Err("Error in subpipeline execution")

            unwrapped_speech = speech.unwrap()

            scs = SentimentClassifiedSpeech(
                id=unwrapped_speech["id"],
                speaker=unwrapped_speech["speaker"],
                topics=unwrapped_speech["topics"],
                text=unwrapped_speech["text"],
                sentiment=unwrapped_speech["sentiment"],
            )

            res.append(scs)
        return Ok(res)

    pipeline = (
        Pipeline.init(input_data=speeches, pipeline_config=PipelineConfig(name="Sentiment Analysis Pipeline"))
        .parallel(SubPipeline.init().exec(Sentiment(config=None)))
        .exec(Formatter(config=FormatterConfig(formatter_function=formatter_final)))
        .compile()
    )

    return (await pipeline).unwrap()
