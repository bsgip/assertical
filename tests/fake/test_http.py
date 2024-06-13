from http import HTTPMethod

import pytest
from httpx import Response

from assertical.asserts.type import assert_list_type
from assertical.fake.http import LoggedRequest, MockedAsyncClient


class MyCustomException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)


@pytest.mark.anyio
async def test_MockedAsyncClient_static_response():
    static_response = Response(200, html="<h1>Mocked Result</h1>")
    client = MockedAsyncClient(static_response)
    uri_1 = "http://foo.bar/123"
    uri_2 = "http://foo.bar.baz/456"
    assert (await client.get(uri_1)) is static_response
    assert (await client.get(uri_2)) is static_response
    assert (await client.get(uri_1)) is static_response

    assert client.call_count_by_method[HTTPMethod.GET] == 3
    assert client.call_count_by_method[HTTPMethod.POST] == 0
    assert client.call_count_by_method[HTTPMethod.DELETE] == 0

    assert (await client.post(uri_1, content="Post Body")) is static_response

    assert client.call_count_by_method[HTTPMethod.GET] == 3
    assert client.call_count_by_method[HTTPMethod.POST] == 1
    assert client.call_count_by_method[HTTPMethod.DELETE] == 0

    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_1), None) == 2
    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_2), None) == 1
    assert client.call_count_by_method_uri.get((HTTPMethod.POST, uri_1), None) == 1
    assert client.call_count_by_method_uri.get((HTTPMethod.DELETE, uri_1), None) is None
    assert client.call_count_by_method_uri.get((HTTPMethod.PATCH, uri_2), None) is None

    assert_list_type(LoggedRequest, client.logged_requests, 4)


@pytest.mark.anyio
async def test_MockedAsyncClient_varied_response():
    response_1 = Response(200, html="<h1>Mocked Result</h1>")
    response_2 = Response(201)
    response_3 = MyCustomException("To be raised")
    response_4 = Response(500)
    client = MockedAsyncClient([response_1, response_2, response_3, response_4])
    uri_1 = "http://foo.bar/123"
    uri_2 = "http://foo.bar.baz/456"
    assert (await client.get(uri_1)) is response_1
    assert (await client.get(uri_2)) is response_2
    with pytest.raises(MyCustomException):
        await client.get(uri_2)
    assert (await client.get(uri_1)) is response_4

    # End of the list of responses
    with pytest.raises(Exception):
        await client.get(uri_1)
    with pytest.raises(Exception):
        await client.get(uri_2)

    assert client.call_count_by_method[HTTPMethod.GET] == 6
    assert client.call_count_by_method[HTTPMethod.POST] == 0
    assert client.call_count_by_method[HTTPMethod.DELETE] == 0

    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_1), None) == 3
    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_2), None) == 3
    assert client.call_count_by_method_uri.get((HTTPMethod.POST, uri_1), None) is None
    assert client.call_count_by_method_uri.get((HTTPMethod.PATCH, uri_2), None) is None

    assert_list_type(LoggedRequest, client.logged_requests, 6)


@pytest.mark.anyio
async def test_MockedAsyncClient_keyed_response():
    response_1 = Response(200, html="<h1>Mocked Result</h1>")
    response_2 = Response(201)
    response_3 = MyCustomException("will be raised")
    response_4 = Response(500)
    uri_1 = "http://foo.bar/123"
    uri_2 = "http://foo.bar.baz/456"
    uri_3 = "http://foo.bar.baz/789"

    client = MockedAsyncClient({uri_1: response_1, uri_2: [response_2, response_3, response_4]})

    assert (await client.get(uri_1)) is response_1
    assert (await client.get(uri_2)) is response_2
    assert (await client.get(uri_1)) is response_1
    with pytest.raises(MyCustomException):
        await client.get(uri_2)
    assert (await client.get(uri_1)) is response_1
    assert (await client.get(uri_2)) is response_4

    # End of the list of responses
    assert (await client.get(uri_1)) is response_1
    with pytest.raises(Exception):
        await client.get(uri_2)  # No more keyed items in the list
    with pytest.raises(Exception):
        await client.get(uri_3)  # This isn't keyed - it will always fail

    assert client.call_count_by_method[HTTPMethod.GET] == 9
    assert client.call_count_by_method[HTTPMethod.POST] == 0
    assert client.call_count_by_method[HTTPMethod.DELETE] == 0

    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_1), None) == 4
    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_2), None) == 4
    assert client.call_count_by_method_uri.get((HTTPMethod.GET, uri_3), None) == 1
    assert client.call_count_by_method_uri.get((HTTPMethod.DELETE, uri_1), None) is None
    assert client.call_count_by_method_uri.get((HTTPMethod.PATCH, uri_2), None) is None

    assert_list_type(LoggedRequest, client.logged_requests, 9)
