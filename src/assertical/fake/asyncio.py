from asyncio import Future
from typing import Any


def create_async_result(result: Any) -> Future:
    """Creates an awaitable result (as a Future) that will return immediately"""
    f: Future = Future()
    f.set_result(result)
    return f
