from typing import Any

import pytest

from assertical.fake.asyncio import create_async_result


@pytest.mark.anyio
@pytest.mark.parametrize("v", [123, "456", None, {"789": 456}, [1, 2, 3]])
async def test_create_async_result(v: Any):
    assert (await create_async_result(v)) == v
