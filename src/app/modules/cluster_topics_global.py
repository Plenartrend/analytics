from typing import Any

import numpy as np
from pipeline.pipeline.step import Step
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from pipeline.types.result import Ok, Result
from sqlalchemy import literal, select

from ..model.model import Topic
from ..utils.db import get_db


class ClusterTopicsGlobal(Step):
    def __init__(self, *, config, session):
        self.config = config
        self.session = session

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        input_value = input_data.unwrap()
        input_embeddings = input_value["embeddings"]
        output_topics = []

        for i, emb in enumerate(input_embeddings):
            async with get_db() as session:
                topic_name = input_value["topics"][i]

                stmt = select(Topic).order_by(Topic.embedding.op("<->")(literal(emb.cpu().numpy()))).limit(1)
                result = await session.execute(stmt)
                closest_topic = result.scalars().first()

            distance = np.linalg.norm(closest_topic.embedding - emb.cpu().numpy()) if closest_topic else None
            if closest_topic is None or distance > self.config.eps:
                new_topic = Topic(name=topic_name, embedding=emb.cpu())
                session.add(new_topic)
                await session.commit()
                closest_topic = new_topic

            output_topics.append({
                "topic_id": closest_topic.id,
                "name": closest_topic.name,
                "embedding": closest_topic.embedding,
            })

        return await pipeline_config.next(Ok({**input_value, "cluster_topics": output_topics}), pipeline_config)
