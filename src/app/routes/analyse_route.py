import json
import logging
import traceback

from podi import Router
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import (
    activity_repository,
    printed_papers_mapping_repository,
    tf_idf_repository,
)
from ..schema import BundestagProtocol
from ..schema.schema import PrintedPaper
from ..services import sentiment_service, tf_idf_service, topic_service

LOGGER = logging.getLogger("analyse_route")

router = Router()


@router.route("analysePrintedPaperEvent")
async def analyse_printed_paper_event(protocol: PrintedPaper, session: AsyncSession):
    try:
        topic_classified_speech = await topic_service.run_topic_analysis_printed_paper_pipeline(
            protocol.id, protocol.title, protocol.text
        )
        topic_classified_stance_speech = await sentiment_service.run_sentiment_analysis_pipeline(
            topic_classified_speech
        )

        await printed_papers_mapping_repository.insert(topic_classified_stance_speech, session)

    except Exception as e:
        traceback.print_exc()
        LOGGER.error(f"Error during analysis of the docuemnt : {e}")
        raise e


@router.route("analyseProtocolEvent")
async def analyse_protocol_event(activity: BundestagProtocol, session: AsyncSession):
    try:
        # topic_classified_speech = await topic_service.run_topic_analysis_protocol_pipeline(
        #    activity.id, activity.speech, session
        # )

        # topic_classified_stance_speech = await sentiment_service.run_sentiment_analysis_pipeline(
        #     topic_classified_speech
        # )

        # await activity_mapping_repository.insert(topic_classified_stance_speech, session)

        # await relevance_repository.calculate_relevance_for_activity(activity.protocol_id, session)

        cnt = await activity_repository.get_activity_cnt_after(activity.person_id, activity.speech_date, session)

        if cnt < 20:
            tfidf_matrix = await tf_idf_service.calculate_tf_idf(activity.person_id, activity.speech_date, session)
            await tf_idf_repository.insert_tfidf(activity.person_id, json.dumps(tfidf_matrix), session)

    except Exception as e:
        traceback.print_exc()
        LOGGER.error(f"Error during analysis: {e}")
        raise e
