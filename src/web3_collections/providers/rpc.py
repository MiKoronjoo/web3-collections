from typing import Optional, Union, Any, List
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
    ) -> None:
        self._uris = deque(endpoint_uris) if endpoint_uris else deque()
        super().__init__(self.current_endpoint, request_kwargs, session)
        self._auto_update = auto_update

    @property
    def current_endpoint(self):
        return self._uris[0] if self._uris else None

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
        for _ in range(max(1, len(self._uris))):
            try:
                raw_response = make_post_request(
                    self.endpoint_uri, request_data, **self.get_request_kwargs()
                )
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

        response = self.decode_rpc_response(raw_response)
        self.logger.debug(
            f"Getting response HTTP. URI: {self.endpoint_uri}, "
            f"Method: {method}, Response: {response}"
        )
        return response
