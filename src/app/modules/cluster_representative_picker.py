from typing import Any

import torch
from pipeline.pipeline.step import Step
from pipeline.types.result import Result, Ok
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse

class ClusterRepresentativePicker(Step):
    def __init__(self, *, config: None):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        labels = speech["labels"]
        topics = speech["topics"]
        embeddings = speech["embeddings"].cpu().numpy()

        representatives = {}
        unique_labels = set(labels)
        for label in unique_labels:
            idxs = [i for i, l in enumerate(labels) if l == label]
            if len(idxs) == 1:
                representatives[label] = topics[idxs[0]]
            else:
                cluster_emb = embeddings[idxs]
                centroid = cluster_emb.mean(axis=0)
                distances = torch.nn.functional.cosine_similarity(torch.from_numpy(cluster_emb), torch.from_numpy(centroid))
                best_idx = idxs[distances.argmax().item()]
                representatives[label] = topics[best_idx]

        return await pipeline_config.next(Ok({**speech, "cluster_reps": representatives}), pipeline_config)