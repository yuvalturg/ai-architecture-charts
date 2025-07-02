import asyncio
import logging
from typing import Union

from fastapi import Body, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse

from . import k8s, pipelines
from .models import GitHubSource, S3Source, URLsSource

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


app = FastAPI()


@app.get("/ping")
def ping():
    return JSONResponse(content={"status": "ok"})


@app.post("/add")
async def add_pipeline(
    payload: Union[GitHubSource, S3Source, URLsSource] = Body(...)
):
    try:
        k8s_name = await asyncio.to_thread(k8s.apply_model_as_secret, payload, replace=True)
        pipeline_id = await asyncio.to_thread(pipelines.add_pipeline, k8s_name, payload.source)
        logger.info(f"Added pipeline {k8s_name}, {pipeline_id=}")
        return JSONResponse(
            content={
                "status": "ok",
                "pipeline_name": k8s_name,
                "pipeline_id": pipeline_id,
            }
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/status")
async def get_pipeline_status(pipeline_name: str):
    try:
        k8s_name = k8s.normalize_name(pipeline_name)
        state = await asyncio.to_thread(pipelines.get_latest_run_state, pipeline_name=k8s_name)
        logger.info(f"Returning state {state} for {pipeline_name=} {k8s_name=}")
        return JSONResponse(content={"state": state})
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.delete("/delete")
async def delete_pipeline(pipeline_name: str):
    try:
        k8s_name = k8s.normalize_name(pipeline_name)
        ret = await asyncio.to_thread(pipelines.delete_pipeline, pipeline_name=k8s_name)
        success = await asyncio.to_thread(k8s.delete_k8s_secret, secret_name=k8s_name)
        logger.info(f"Deleted pipeline {pipeline_name} {k8s_name=} {success=}")
        return JSONResponse(content=ret | {"success": success})
    except LookupError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
