import logging
import traceback
from pprint import pprint

from podi import Router

from ..repositories import activity_mapping_repository
from ..schema import BundestagProtocol
from ..services import sentiment_service, topic_service

LOGGER = logging.getLogger("analyse_route")

router = Router()


@router.route("analyseEvent")
async def analyse_event(protocol: BundestagProtocol):
    try:
        topic_classified_speech = await topic_service.run_topic_analysis_pipeline(protocol.id, protocol.speech)
        topic_classified_stance_speech = await sentiment_service.run_sentiment_analysis_pipeline(
            topic_classified_speech
        )
        await activity_mapping_repository.insert(topic_classified_stance_speech)
        pprint(topic_classified_stance_speech.model_dump(), width=120)

    except Exception as e:
        traceback.print_exc()
        LOGGER.error(f"Error during analysis: {e}")
