from fastapi import FastAPI

from .server import router

app = FastAPI()
app.include_router(router)
