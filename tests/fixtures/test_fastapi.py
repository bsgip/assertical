from contextlib import asynccontextmanager
import json

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from assertical.fixtures.fastapi import start_app_with_client, start_uvicorn_server


# Test App Definition
def generate_test_app():
    """Generates an app with two endpoints:
    /hello_world (This is added during app creation)
    /added_later (This will be added when the lifespan_manager executes on startup)"""

    @asynccontextmanager
    async def lifespan_manager(app: FastAPI):
        """This will install a new endpoint during application startup"""

        async def added_later():
            return "Added Later"

        app.router.add_api_route("/added_later", added_later)
        yield

    test_app = FastAPI(lifespan=lifespan_manager)

    @test_app.get("/hello_world")
    async def hello_world():
        return {"msg": "Hello World"}

    @test_app.post("/hello_world")
    async def hello_world_create():
        return None

    return test_app

@pytest.mark.anyio
async def test_client_content_type_set():
    """Ensures that a request content-type header is only set for bodied requests."""
    app = generate_test_app()

    async with start_app_with_client(app) as client:
        body = json.dumps({"msg": "hello world"})
        response = await client.post("/hello_world", content=body)
        assert response.request.headers.get("content-type") == "application/json"
        
        response = await client.get("/hello_world")
        assert not response.request.headers.get("content-type")


@pytest.mark.parametrize("multi_iteration", [1, 2, 3])
@pytest.mark.anyio
async def test_uvicorn_running_app(multi_iteration):
    """Tests that start_uvicorn_server runs a test app and calls all lifespan managers"""

    # Why are we running this over multiple iterations? Because we hit an issue with python3.10 socket impl that when
    # executed sequentially - the resulting data varied and caused our code to fail. This is to cover that particular
    # quirk - We have a fix to avoid this now but this multi_iteration stuff is a safety against future regressions
    print(multi_iteration)

    app = generate_test_app()

    async with start_uvicorn_server(app) as base_uri:
        client = AsyncClient()
        response = await client.get(base_uri + "/hello_world")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.content.decode() == '{"msg":"Hello World"}'

        response = await client.get(base_uri + "/added_later")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.content.decode() == '"Added Later"'

        response = await client.get(base_uri + "/missing_route")
        assert response.status_code == 404


@pytest.mark.anyio
async def test_asgi_running_app():
    """Tests that running an ASGI app directly (with start_app_with_client) calls all lifespan managers"""
    app = generate_test_app()

    async with start_app_with_client(app) as client:
        response = await client.get("/hello_world")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.content.decode() == '{"msg":"Hello World"}'

        response = await client.get("/added_later")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/json"
        assert response.content.decode() == '"Added Later"'

        response = await client.get("/missing_route")
        assert response.status_code == 404
