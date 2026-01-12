from app.model.model import ActivityMapping
from app.schema.schema import SentimentClassifiedSpeech
from app.utils.db import get_db


async def insert(sentiment_classified_speech: SentimentClassifiedSpeech):
    for i in range(len(sentiment_classified_speech.topics)):
        async with get_db() as db:
            db.add(
                ActivityMapping(
                    activity_id=sentiment_classified_speech.id,
                    topic_id=sentiment_classified_speech.topics[i].id,
                    sentiment_value=sentiment_classified_speech.sentiment[i].stance,
                    sentiment_reason=sentiment_classified_speech.sentiment[i].explanation,
                )
            )
            await db.commit()
