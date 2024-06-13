from typing import AsyncGenerator

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


async def start_app_with_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Creates an AsyncClient for a test app and returns it as an AsyncGenerator for use with a fixture:

    async with start_app_with_client(app) as client:
        yield client

    The app will be registered with a LifespanManager to ensure startup/shutdown events are fired
    """

    async with LifespanManager(app):  # This ensures that startup events are fired when the app starts
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:  # type: ignore
            yield c
