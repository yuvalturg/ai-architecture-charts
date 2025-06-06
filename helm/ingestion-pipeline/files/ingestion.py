import os
import time

from kfp import dsl
from kfp import Client
from kfp import compiler

# Values from helm chart
LLAMA_STACK_VERSION = '{{ .Chart.AppVersion }}'
SECRET_NAME = '{{ include "ingestion-pipeline.name" . | trim }}'
PIPELINE_NAME = SECRET_NAME + '-pipeline'


@dsl.component(
    base_image="python:3.10",
    packages_to_install=[
        "boto3"
    ])
def fetch_from_s3(output_dir: dsl.OutputPath()):
    import os
    import boto3

    # S3 Config
    bucket_name = os.environ.get('BUCKET_NAME')
    minio_endpoint = os.environ.get('ENDPOINT_URL')
    minio_access_key = os.environ.get('ACCESS_KEY_ID')
    minio_secret_key = os.environ.get('SECRET_ACCESS_KEY')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    print(f"Created output directory: {output_dir}")

    # Connect to MinIO
    print(f"Connecting to MinIO at {minio_endpoint}")
    s3 = boto3.client(
        "s3",
        endpoint_url=minio_endpoint,
        aws_access_key_id=minio_access_key,
        aws_secret_access_key=minio_secret_key,
        verify=False
    )

    # List and download objects
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name)

    print(f"Downloading files from bucket: {bucket_name}")
    downloaded_files = []
    for page in pages:
        for obj in page.get("Contents", []):
            key = obj["Key"]
            file_path = os.path.join(output_dir, os.path.basename(key))
            print(f"Downloading: {key} -> {file_path}")
            s3.download_file(bucket_name, key, file_path)
            downloaded_files.append(file_path)

    print(f"Downloaded {len(downloaded_files)} files to {output_dir}")

    if not downloaded_files:
        raise Exception(f"No files found in bucket: {bucket_name}. Please check your bucket configuration.")

    print(f"Contents of output directory: {os.listdir(output_dir)}")


@dsl.component(base_image="python:3.10")
def fetch_from_urls(output_dir: dsl.OutputPath()):
    print(f"Storing documents will fetch from URLS env var")


@dsl.component(
    base_image="python:3.10",
    packages_to_install=[
        "GitPython"
    ])
def fetch_from_github(output_dir: dsl.OutputPath()):
    import os
    import git
    import tempfile
    import shutil
    os.makedirs(output_dir, exist_ok=True)
    token = os.getenv("GIT_TOKEN")
    url = os.getenv("GIT_URL")
    if token:
        if url.startswith("https://"):
            url = url.replace("https://", f"https://{token}@")
        else:
            raise ValueError("Only HTTPS URLs support token authentication")
    with tempfile.TemporaryDirectory() as tmp_dir:
        git.Repo.clone_from(url, tmp_dir, branch=os.getenv("GIT_BRANCH"), depth=1, single_branch=True)
        src_dir = os.path.join(tmp_dir, os.getenv("GIT_PATH"))
        if os.path.isdir(src_dir):
            for entry in os.scandir(src_dir):
                if entry.is_file():
                    print(f"Copying {entry.path} to {output_dir}")
                    shutil.copy2(entry.path, os.path.join(output_dir, entry.name))
        else:
            raise RuntimeError(f"Directory {src_dir} not found in the repo.")


@dsl.component(
    base_image="python:3.10",
    packages_to_install=[
        f"llama-stack-client=={LLAMA_STACK_VERSION}",
        "fire",
        "requests",
        "docling",
        "docling-core"
    ])
def store_documents(llamastack_base_url: str, input_dir: dsl.InputPath()):
    import os
    from pathlib import Path

    from llama_stack_client import LlamaStackClient
    from llama_stack_client.types import Document as LlamaStackDocument

    # Import docling libraries
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling_core.transforms.chunker.hybrid_chunker import HybridChunker
    from docling_core.types.doc.labels import DocItemLabel

    os.environ["EASYOCR_MODULE_PATH"] = "/tmp/.EasyOCR"

    # Configuring the vector database
    name = os.environ.get('NAME')
    version = os.environ.get('VERSION')
    embedding_model = os.environ.get('EMBEDDING_MODEL')
    vector_db_name = f"{name}-v{version}".replace(" ", "-").replace(".", "-")

    # Setup docling components
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.MD,
            InputFormat.DOCX,
            InputFormat.ASCIIDOC,
            InputFormat.JSON_DOCLING,
            InputFormat.HTML
        ],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    chunker = HybridChunker()
    llama_documents = []
    i = 0
    # Process each file with docling (chunking)
    input_files = []
    if os.getenv("URLS"):
        input_files = os.getenv("URLS","").strip("[]").split()
    else:
        input_files = [str(p) for p in Path(input_dir).iterdir() if p.is_file()]
    if not input_files:
        raise RuntimeError("No input files found")
    print(f"Input files: {input_files}")
    for file_path in input_files:
        print(f"Processing {file_path} with docling...")
        try:
            docling_doc = converter.convert(source=file_path).document
            chunks = chunker.chunk(docling_doc)
            chunk_count = 0

            for chunk in chunks:
                if any(
                    c.label in [DocItemLabel.TEXT, DocItemLabel.PARAGRAPH, DocItemLabel.TABLE,
                               DocItemLabel.PAGE_HEADER, DocItemLabel.PAGE_FOOTER,
                               DocItemLabel.TITLE, DocItemLabel.PICTURE, DocItemLabel.CHART,
                               DocItemLabel.DOCUMENT_INDEX, DocItemLabel.SECTION_HEADER]
                    for c in chunk.meta.doc_items
                ):
                    i += 1
                    chunk_count += 1
                    llama_documents.append(
                        LlamaStackDocument(
                            document_id=f"doc-{i}",
                            content=chunk.text,
                            mime_type='text/plain',
                            metadata={"source": os.path.basename(file_path)},
                        )
                    )
            print(f"Created {chunk_count} chunks from {file_path}")

        except Exception as e:
            error_message = str(e)
            print(f"Error processing {file_path}: {error_message}")

    total_chunks = len(llama_documents)
    print(f"Total valid chunks prepared: {total_chunks}")

    # Add error handling for zero chunks
    if total_chunks == 0:
        raise Exception("No valid chunks were created. Check document processing errors above.")

    # Step 3: Register vector database and store chunks with embeddings
    client = LlamaStackClient(base_url=llamastack_base_url)
    print("Registering db")
    try:
        client.vector_dbs.register(
            vector_db_id=vector_db_name,
            embedding_model=embedding_model,
            embedding_dimension=384,
            provider_id="pgvector",
        )
        print("Vector DB registered successfully")
    except Exception as e:
        error_message = str(e)
        print(f"Failed to register vector DB: {error_message}")
        raise Exception(f"Vector DB registration failed: {error_message}")

    try:
        print(f"Inserting {total_chunks} chunks into vector database")
        client.tool_runtime.rag_tool.insert(
            documents=llama_documents,
            vector_db_id=vector_db_name,
            chunk_size_in_tokens=512,
        )
        print("Documents successfully inserted into the vector DB")

    except Exception as e:
        print("Embedding insert failed:", e)
        raise Exception(f"Failed to insert documents into vector DB: {e}")


@dsl.pipeline(name="fetch-and-store-pipeline")
def s3_pipeline():
    from kfp import kubernetes
    secret_key_to_env = {
            'SOURCE': 'SOURCE',
            'EMBEDDING_MODEL': 'EMBEDDING_MODEL',
            'NAME': 'NAME',
            'VERSION': 'VERSION',
            'ACCESS_KEY_ID': 'ACCESS_KEY_ID',
            'SECRET_ACCESS_KEY': 'SECRET_ACCESS_KEY',
            'ENDPOINT_URL': 'ENDPOINT_URL',
            'BUCKET_NAME': 'BUCKET_NAME',
            'REGION': 'REGION'
    }

    fetch_task = fetch_from_s3()
    fetch_task.set_caching_options(False)
    store_task = store_documents(
        llamastack_base_url=os.environ["LLAMASTACK_BASE_URL"],
        input_dir=fetch_task.outputs["output_dir"]
    )
    store_task.set_caching_options(False)

    kubernetes.use_secret_as_env(
        task=fetch_task,
        secret_name=SECRET_NAME,
        secret_key_to_env=secret_key_to_env
    )

    kubernetes.use_secret_as_env(
        task=store_task,
        secret_name=SECRET_NAME,
        secret_key_to_env=secret_key_to_env
    )


@dsl.pipeline(name="fetch-and-store-pipeline")
def url_pipeline():
    from kfp import kubernetes
    secret_key_to_env = {
        'SOURCE': 'SOURCE',
        'EMBEDDING_MODEL': 'EMBEDDING_MODEL',
        'NAME': 'NAME',
        'VERSION': 'VERSION',
        'URLS': 'URLS'
    }

    fetch_task = fetch_from_urls()
    fetch_task.set_caching_options(False)
    store_task = store_documents(
        llamastack_base_url=os.environ["LLAMASTACK_BASE_URL"],
        input_dir=fetch_task.outputs["output_dir"]
    )
    store_task.set_caching_options(False)

    kubernetes.use_secret_as_env(
        task=store_task,
        secret_name=SECRET_NAME,
        secret_key_to_env=secret_key_to_env
    )


@dsl.pipeline(name="fetch-and-store-pipeline")
def github_pipeline():
    from kfp import kubernetes
    secret_key_to_env = {
        'SOURCE': 'SOURCE',
        'EMBEDDING_MODEL': 'EMBEDDING_MODEL',
        'NAME': 'NAME',
        'VERSION': 'VERSION',
        'URL': 'GIT_URL',
        'PATH': 'GIT_PATH',
        'TOKEN': 'GIT_TOKEN',
        'BRANCH': 'GIT_BRANCH'
    }

    fetch_task = fetch_from_github()
    fetch_task.set_caching_options(False)
    store_task = store_documents(
        llamastack_base_url=os.environ["LLAMASTACK_BASE_URL"],
        input_dir=fetch_task.outputs["output_dir"]
    )
    store_task.set_caching_options(False)

    kubernetes.use_secret_as_env(
        task=fetch_task,
        secret_name=SECRET_NAME,
        secret_key_to_env=secret_key_to_env
    )

    kubernetes.use_secret_as_env(
        task=store_task,
        secret_name=SECRET_NAME,
        secret_key_to_env=secret_key_to_env
    )


# 1. Compile pipeline to a file
pipeline_yaml = "/tmp/fetch_chunk_embed_pipeline.yaml"

if os.environ.get('SOURCE') == "S3":
    print("S3 pipeline")
    compiler.Compiler().compile(
        pipeline_func=s3_pipeline,
        package_path=pipeline_yaml
    )
elif os.environ.get('SOURCE') == "URL":
    print("URL pipeline")
    compiler.Compiler().compile(
        pipeline_func=url_pipeline,
        package_path=pipeline_yaml
    )
elif os.environ.get('SOURCE') == "GITHUB":
    print("GITHUB pipeline")
    compiler.Compiler().compile(
        pipeline_func=github_pipeline,
        package_path=pipeline_yaml
    )

# 2. Connect to KFP
client = Client(
    host=os.environ["DS_PIPELINE_URL"],
    verify_ssl=False
)

# 3. Upload pipeline
pipeline_id = client.get_pipeline_id(PIPELINE_NAME)

experiments = client.list_experiments()
experiment_id = experiments.experiments[0].experiment_id

if pipeline_id is None:
    uploaded_pipeline = client.upload_pipeline(
        pipeline_package_path=pipeline_yaml,
        pipeline_name=PIPELINE_NAME,
    )
    pipeline_id = uploaded_pipeline.pipeline_id
    versions = client.list_pipeline_versions(pipeline_id)
    version_id = [v.pipeline_version_id for v in versions.pipeline_versions if v.display_name == PIPELINE_NAME][0]
else:
    version_name = f"{PIPELINE_NAME}-{time.strftime('%Y%m%d-%H%M%S')}"
    uploaded_pipeline = client.upload_pipeline_version(
        pipeline_package_path=pipeline_yaml,
        pipeline_id=pipeline_id,
        pipeline_version_name=version_name,
    )
    version_id = uploaded_pipeline.pipeline_version_id

# 4. Run the pipeline
run = client.run_pipeline(
    pipeline_id=pipeline_id,
    version_id=version_id,
    experiment_id=experiment_id,
    job_name=f"fetch-store-run-{os.environ.get('SOURCE').lower()}"
)

print(f"Pipeline submitted! Run ID: {run.run_id}")
