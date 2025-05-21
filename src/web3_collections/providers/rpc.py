from threading import Thread
from typing import Optional, Union, Any, Iterable
from collections import deque

from requests.exceptions import RequestException
from eth_typing import URI
from web3.providers.rpc.rpc import (
    HTTPProvider,
    ExceptionRetryConfiguration,
    handle_request_caching,
    Empty,
    empty,
    RPCEndpoint,
    RPCResponse
)


class MultiEndpointHTTPProvider(HTTPProvider):
    def __init__(
            self,
            endpoint_uris: Optional[Iterable[Union[URI, str]]] = None,
            request_kwargs: Optional[Any] = None,
            session: Optional[Any] = None,
            exception_retry_configuration: Optional[
                Union[ExceptionRetryConfiguration, Empty]
            ] = empty,
            auto_update: bool = True,
            **kwargs: Any,
    ) -> None:
        if endpoint_uris is None:
            endpoint_uris = []
        self._uris = deque(map(URI, endpoint_uris))
        super().__init__(self.current_endpoint, request_kwargs, session, exception_retry_configuration, **kwargs)
        self._auto_update = auto_update

    @property
    def current_endpoint(self) -> Optional[URI]:
        return self._uris[0] if self._uris else None

    @property
    def next_endpoint(self) -> Optional[URI]:
        return self._uris[1] if len(self._uris) > 1 else None

    def sort_endpoints(self):
        results = {}
        request_data = self.encode_rpc_request('eth_blockNumber', ())
        request_kwargs: dict = self.get_request_kwargs()

        def temp_func(uri):
            try:
                raw_response = self._request_session_manager.make_post_request(uri, request_data, **request_kwargs)
            except RequestException as ex:
                self.logger.error(
                    f"{type(ex)}: from {uri}: {ex}"
                )
                return
            response = self.decode_rpc_response(raw_response)
            results[uri] = int(response['result'], 16)

        threads = []
        for endpoint_uri in self._uris:
            t = Thread(target=temp_func, args=(endpoint_uri,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()

        self._uris = deque(sorted(self._uris, key=lambda x: results.get(x, 0), reverse=True))
        self.endpoint_uri = URI(self.current_endpoint)

    def update_endpoint(self):
        self._uris.rotate(-1)
        self.logger.debug(
            f"Updating URI from {self.endpoint_uri} to {self.current_endpoint}"
        )
        self.endpoint_uri = URI(self.current_endpoint)

    @handle_request_caching
    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        self.logger.debug(
            f"Making request HTTP. URI: {self.endpoint_uri}, Method: {method}"
        )
        request_data = self.encode_rpc_request(method, params)
        for _ in range(max(1, len(self._uris))):
            try:
                raw_response = self._make_request(method, request_data)
                response = self.decode_rpc_response(raw_response)
                if 'error' in response and 'execution reverted' not in response['error'].get('message', ''):
                    raise ValueError(response['error'])
            except (RequestException, ValueError) as ex:
                if not self._auto_update:
                    raise
                self.logger.error(
                    f"{type(ex)}: from {self.endpoint_uri}: {ex}"
                )
                self.update_endpoint()
            else:
                break
        else:
            raise RequestException("All endpoints got error")

        self.logger.debug(
            f"Getting response HTTP. URI: {self.endpoint_uri}, "
            f"Method: {method}, Response: {response}"
        )
        return response
