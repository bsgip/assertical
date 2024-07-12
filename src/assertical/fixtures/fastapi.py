from typing import AsyncGenerator, Optional

from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx._types import AuthTypes


async def start_app_with_client(
    app: FastAPI, client_auth: Optional[AuthTypes] = None
) -> AsyncGenerator[AsyncClient, None]:
    """Creates an AsyncClient for a test app and returns it as an AsyncGenerator for use with a fixture:

    async with start_app_with_client(app) as client:
        yield client

    The app will be registered with a LifespanManager to ensure startup/shutdown events are fired

    app: The test app to generate a running instance and client for
    client_auth: if specified will ensure all requests made by this client will use this auth. Default is None
    """

    async with LifespanManager(app):  # This ensures that startup events are fired when the app starts
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", auth=client_auth) as c:  # type: ignore # noqa: E501
            yield c
