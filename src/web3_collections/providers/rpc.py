from threading import Thread
from typing import Optional, Union, Any, List, Callable
from collections import deque

from requests.exceptions import RequestException
from eth_typing import URI
from web3._utils.request import make_post_request
from web3.types import RPCEndpoint, RPCResponse
from web3 import HTTPProvider


class MultiEndpointHTTPProvider(HTTPProvider):
    def __init__(
            self,
            endpoint_uris: Optional[List[Union[URI, str]]] = None,
            request_kwargs: Optional[Any] = None,
            session: Optional[Any] = None,
            auto_update: bool = True,
            before_endpoint_update: Callable = None,
    ) -> None:
        self._uris = deque(endpoint_uris) if endpoint_uris else deque()
        super().__init__(self.current_endpoint, request_kwargs, session)
        self._auto_update = auto_update
        self.before_endpoint_update = before_endpoint_update

    @property
    def current_endpoint(self):
        return self._uris[0] if self._uris else None

    @property
    def next_endpoint(self):
        return self._uris[1] if len(self._uris) > 1 else None

    def sort_endpoints(self):
        results = {}
        request_data = self.encode_rpc_request('eth_blockNumber', ())
        request_kwargs = self.get_request_kwargs()

        def temp_func(uri):
            raw_response = make_post_request(uri, request_data, **request_kwargs)
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

    def make_request(self, method: RPCEndpoint, params: Any) -> RPCResponse:
        self.logger.debug(
            f"Making request HTTP. URI: {self.endpoint_uri}, Method: {method}"
        )
        request_data = self.encode_rpc_request(method, params)
        while i := 0 < max(1, len(self._uris)):
            try:
                raw_response = make_post_request(
                    self.endpoint_uri, request_data, **self.get_request_kwargs()
                )
                response = self.decode_rpc_response(raw_response)
                if 'error' in response:
                    raise ValueError(response['error'])
            except (RequestException, ValueError) as ex:
                if not self._auto_update:
                    raise
                self.logger.error(
                    f"{type(ex)}: from {self.endpoint_uri}: {ex}"
                )
                if self.before_endpoint_update is None:
                    self.update_endpoint()
                    i += 1
                else:
                    current_endpoint = self.current_endpoint
                    while i < max(1, len(self._uris)):
                        is_ok = self.before_endpoint_update(current_endpoint, self.next_endpoint, ex)
                        self.update_endpoint()
                        i += 1
                        if is_ok:
                            break
            else:
                break
        else:
            raise RequestException("All endpoints got error")

        self.logger.debug(
            f"Getting response HTTP. URI: {self.endpoint_uri}, "
            f"Method: {method}, Response: {response}"
        )
        return response
