import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import uvicorn
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from httpx._types import AuthTypes


class UvicornTestServer(uvicorn.Server):
    """Creates a uvicorn test server for serving a test FastAPI app. The server will startup and listen
    on a specific host/port.

    Originally adapted from https://github.com/miguelgrinberg/python-socketio/issues/332#issuecomment-712928157"""

    def __init__(self, app: FastAPI, host: str, port: int = 13842):
        """Create a Uvicorn test server

        Args:
            app (FastAPI, optional): the FastAPI app.
            host (str, optional): the host ip. Defaults to HOST.
            port (int, optional): the port. Defaults to PORT.
        """
        self._startup_done = asyncio.Event()
        super().__init__(config=uvicorn.Config(app, host=host, port=port))

    async def startup(self, sockets: Optional[list] = None) -> None:
        """Override uvicorn startup"""
        await super().startup(sockets=sockets)
        self.config.setup_event_loop()
        self._startup_done.set()

    async def up(self) -> None:
        self._serve_task = asyncio.create_task(self.serve())
        await self._startup_done.wait()

    async def down(self) -> None:
        self.should_exit = True
        await self._serve_task


@asynccontextmanager
async def start_app_with_client(
    app: FastAPI, client_auth: Optional[AuthTypes] = None
) -> AsyncGenerator[AsyncClient, None]:
    """Creates an AsyncClient for a test app and returns it as an AsyncGenerator for use with a fixture:

    Usage:

    async with start_app_with_client(app) as client:
        yield client

    The app will be registered with a LifespanManager to ensure startup/shutdown events are fired

    app: The test app to generate a running instance and client for
    client_auth: if specified will ensure all requests made by this client will use this auth. Default is None
    """

    async with LifespanManager(app):  # This ensures that startup events are fired when the app starts
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", auth=client_auth) as c:  # type: ignore # noqa: E501
            yield c


@asynccontextmanager
async def start_uvicorn_server(app: FastAPI, host: str = "127.0.0.1", port: int = 13823) -> AsyncGenerator[str, None]:
    """Starts uvicorn server for a test app and tears everything down after async generator finishes. Returns the HTTP
    base URI for that server (including port) as a string.

    This function does NOT search for available listen ports. If the port is unavailable for listening this will raise
    an exception.

    Usage:
    async with run_uvicorn_server(app) as base_uri:
        yield base_uri

    Return Example: 'http://127.0.0.1:1234'
    """
    server = UvicornTestServer(app=app, host=host, port=port)
    await server.up()

    # Extract the listening socket - this isn't the most robust method but haven't found a counterexample yet
    listening_socket = getattr(server.servers[0].sockets[0], "_sock", None)
    if listening_socket is None:
        raise Exception("Unable to find listening socket")
    (host, port) = listening_socket.getsockname()
    yield f"http://{host}:{port}"

    await server.down()
