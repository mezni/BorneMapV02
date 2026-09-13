# Ingestion Pipeline Orchestrator
# TODO: Add stages configuration


class IngestionPipeline:
    """Ingestion pipeline orchestrator.

    Currently configured with 0 stages. Stages will be defined
    in configs/pipelines.yaml and loaded at runtime.
    """

    def __init__(self, pipeline_name: str = "default"):
        self.pipeline_name = pipeline_name
        self.stages = []

    def add_stage(self, stage):
        """Add a stage to the pipeline."""
        self.stages.append(stage)

    def run(self, document):
        """Run the ingestion pipeline on a document.

        With 0 stages, this simply returns the document unchanged.
        """
        for stage in self.stages:
            document = stage(document)
        return document