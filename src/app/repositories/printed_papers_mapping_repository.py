from sqlalchemy.ext.asyncio import AsyncSession

from ..model.model import PrintedPaperMapping
from ..schema.schema import SentimentClassifiedSpeech
from ..utils.db import get_db


async def insert(sentiment_classified_speech: SentimentClassifiedSpeech, transaction: AsyncSession = None):
    for i in range(len(sentiment_classified_speech.topics)):
        el = PrintedPaperMapping(
            printed_paper_id=sentiment_classified_speech.id,
            topic_id=sentiment_classified_speech.topics[i].id,
            sentiment_value=sentiment_classified_speech.sentiment[i].stance,
            sentiment_reason=sentiment_classified_speech.sentiment[i].explanation,
        )
        if transaction:
            transaction.add(el)
        else:
            async with get_db() as db:
                db.add(el)
                await db.commit()
