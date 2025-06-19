from typing import Union

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import JSONResponse

from . import k8s, pipelines
from .models import GitHubSource, S3Source, URLsSource

app = FastAPI()

@app.get("/ping")
def ping():
    return JSONResponse(content={"status": "ok"})

@app.post("/add_pipeline")
async def add_pipeline(
    payload: Union[GitHubSource, S3Source, URLsSource] = Body(...)
):
    try:
        payload.set_vector_db_name()
        k8s.apply_model_as_secret(payload, replace=True)
        pipelines.add_pipeline(payload.k8s_name(), payload.source)
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

    return JSONResponse(content={"status": "ok", "secret": payload.k8s_name()})
