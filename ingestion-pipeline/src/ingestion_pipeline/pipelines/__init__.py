import os
import tempfile
import time

from kfp import Client, compiler

from . import pipelines

pipeline_dict = {
    "S3": pipelines.s3_pipeline,
    "URL": pipelines.url_pipeline,
    "GITHUB": pipelines.github_pipeline
}

def add_pipeline(secret_name: str, source: str):
    print(f"Pipeline source: {secret_name} {source}")

    pipeline_name = secret_name + "-pipeline"

    if source not in pipeline_dict:
        raise RuntimeError(f"Source {source} not defined")

    pipeline_params = {
        "secret_name": secret_name,
        "llamastack_base_url": os.environ["LLAMASTACK_BASE_URL"]
    }

    with tempfile.NamedTemporaryFile(suffix=".yaml") as tmp:
        compiler.Compiler().compile(
            pipeline_func=pipeline_dict[source](**pipeline_params),
            package_path=tmp.name,
        )

        tmp.flush()

        # 2. Connect to KFP
        client = Client(
            host=os.environ["DS_PIPELINE_URL"],
            verify_ssl=False
        )

        # 3. Upload pipeline
        pipeline_id = client.get_pipeline_id(pipeline_name)

        experiments = client.list_experiments()
        experiment_id = experiments.experiments[0].experiment_id

        if pipeline_id is None:
            uploaded_pipeline = client.upload_pipeline(
                pipeline_package_path=tmp.name,
                pipeline_name=pipeline_name,
            )
            pipeline_id = uploaded_pipeline.pipeline_id
            versions = client.list_pipeline_versions(pipeline_id)
            version_id = [v.pipeline_version_id for v in versions.pipeline_versions if v.display_name == pipeline_name][0]
        else:
            version_name = f"{pipeline_name}-{time.strftime('%Y%m%d-%H%M%S')}"
            uploaded_pipeline = client.upload_pipeline_version(
                pipeline_package_path=tmp.name,
                pipeline_id=pipeline_id,
                pipeline_version_name=version_name,
            )
            version_id = uploaded_pipeline.pipeline_version_id

    run = client.run_pipeline(
        pipeline_id=pipeline_id,
        version_id=version_id,
        experiment_id=experiment_id,
        job_name=f"fetch-store-run-{source.lower()}"
    )

    print(f"Pipeline submitted! Run ID: {run.run_id}")
