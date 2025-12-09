from pprint import pprint
from app.schema import BundestagProtocol
from app.services import topic_service, sentiment_service
from app.utils.helper.visualizer import generate_speech_graph
from kadi import Router

router = Router()


@router.route("analyseEvent")
async def analyse_event(protocol: BundestagProtocol):
    speeches = protocol.speeches

    topic_classified_speeches = await topic_service.run_topic_analysis_pipeline(speeches)
    topic_classified_stance_speeches = await sentiment_service.run_sentiment_analysis_pipeline(
        topic_classified_speeches)
    pprint([a.model_dump() for a in topic_classified_stance_speeches], width=120)

    generate_speech_graph(topic_classified_stance_speeches, 0.4)
