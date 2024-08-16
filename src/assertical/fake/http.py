from asyncio import Semaphore, TimeoutError, wait_for
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional, Union

from httpx import Response
from httpx._types import HeaderTypes, RequestContent

# HTTPMethod is only defined in python >= 3.11
try:
    from http import HTTPMethod  # type: ignore
except ImportError:

    class HTTPMethod(Enum):  # type: ignore
        DELETE = auto()
        GET = auto()
        HEAD = auto()
        POST = auto()
        PATCH = auto()
        PUT = auto()


@dataclass
class LoggedRequest:
    """For MockedAsyncClient - keeps a simplified log of outgoing requests"""

    method: str
    uri: str
    headers: Optional[HeaderTypes]
    content: Optional[Any] = None


class MockedAsyncClient:
    """Looks similar to httpx AsyncClient() but returns a mocked response or raises an error

    Can be fed either a static result in the form of a Response/Exception or a dictionary keyed by URI that
    will return dynamic results depending on incoming URI

    If fed a list - subsequent calls will work through the list
    """

    logged_requests: list[LoggedRequest]
    call_count_by_method: dict[HTTPMethod, int]
    call_count_by_method_uri: dict[tuple[HTTPMethod, str], int]

    result: Optional[Union[Response, Exception, list[Union[Response, Exception]]]]
    results_by_uri: dict[str, Union[Response, Exception, list[Union[Response, Exception]]]]

    request_semaphore: Semaphore

    def __init__(self, result: Union[Response, Exception, dict, list[Union[Response, Exception]]]) -> None:
        self.set_results(result)

    def set_results(self, result: Union[Response, Exception, dict, list[Union[Response, Exception]]]) -> None:
        """Re-initialises the behaviour of this mock"""
        self.call_count_by_method = dict([(m, 0) for m in HTTPMethod])
        self.call_count_by_method_uri = {}

        if isinstance(result, dict):
            self.results_by_uri = result
            self.result = None
        else:
            self.results_by_uri = {}
            self.result = result

        self.logged_requests = []
        self.request_semaphore = Semaphore(value=0)

    async def __aenter__(self) -> "MockedAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        return False

    def _raise_or_return(self, result: Union[Response, Exception, list[Union[Response, Exception]]]) -> Response:

        self.request_semaphore.release()  # Indicate that we have a request

        if isinstance(result, list):
            if len(result) > 0:
                next_result = result.pop(0)
                return self._raise_or_return(next_result)
            else:
                raise Exception("Mocking error - no more responses/errors in list.")
        elif isinstance(result, Exception):
            raise result
        elif isinstance(result, Response):
            return result
        else:
            raise Exception(f"Mocking error - unknown type: {type(result)} {result}")

    async def make_request(
        self,
        method: HTTPMethod,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        self.call_count_by_method[method] = self.call_count_by_method[method] + 1
        method_uri_key = (method, url)
        if method_uri_key in self.call_count_by_method_uri:
            self.call_count_by_method_uri[method_uri_key] = self.call_count_by_method_uri[method_uri_key] + 1
        else:
            self.call_count_by_method_uri[method_uri_key] = 1

        data_to_submit: Any = content if content is not None else (json if json is not None else data)

        self.logged_requests.append(LoggedRequest(method=method.name, uri=url, headers=headers, content=data_to_submit))

        uri_specific_result = self.results_by_uri.get(url, None)
        if uri_specific_result is not None:
            return self._raise_or_return(uri_specific_result)

        if self.result is None:
            raise Exception(f"Mocking error - no mocked result for {url}")
        return self._raise_or_return(self.result)

    async def get(
        self,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        return await self.make_request(HTTPMethod.GET, url=url, headers=headers, content=content, json=json, data=data)

    async def post(
        self,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        return await self.make_request(HTTPMethod.POST, url=url, headers=headers, content=content, json=json, data=data)

    async def put(
        self,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        return await self.make_request(HTTPMethod.PUT, url=url, headers=headers, content=content, json=json, data=data)

    async def delete(
        self,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        return await self.make_request(
            HTTPMethod.DELETE, url=url, headers=headers, content=content, json=json, data=data
        )

    async def patch(
        self,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        return await self.make_request(
            HTTPMethod.PATCH, url=url, headers=headers, content=content, json=json, data=data
        )

    async def head(
        self,
        url: str,
        content: Optional[RequestContent] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        headers: Optional[HeaderTypes] = None,
    ) -> Response:
        return await self.make_request(HTTPMethod.HEAD, url=url, headers=headers, content=content, json=json, data=data)

    async def wait_for_request(self, timeout_seconds: float) -> bool:
        """Waits for up to timeout_seconds for a HTTP request to be made to this client. If a request
        has already been made before this function call - it will return immediately.

        Each call to wait_for_request will "consume" one request such that future calls will require
        additional requests to be made before returning

        Returns True if a request was "consumed" or False if the timeout was hit"""
        try:

            await wait_for(self.request_semaphore.acquire(), timeout_seconds)
        except TimeoutError:
            return False

        return True

    async def wait_for_n_requests(self, n: int, timeout_seconds: float) -> bool:
        """Waits for up to timeout_seconds for at least n GET/POST requests to be made to this client. Requests made
        before the wait occurred will count towards n.

        Each call to wait_for_n_requests will "consume" n requests such that future calls will require
        additional requests to be made before returning

        Returns True if n requests were "consumed" or False if the timeout was hit"""
        try:
            remaining_timeout_seconds = timeout_seconds
            for _ in range(n):
                start = datetime.now()
                await wait_for(self.request_semaphore.acquire(), remaining_timeout_seconds)
                remaining_timeout_seconds = remaining_timeout_seconds - (datetime.now() - start).seconds

        except TimeoutError:
            return False

        return True
