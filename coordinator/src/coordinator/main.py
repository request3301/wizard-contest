import asyncio

from fastapi import FastAPI

from .coordinator import Coordinator, router

app = FastAPI()
app.include_router(router)

coordinator = Coordinator()
asyncio.create_task(coordinator.start_polling())
