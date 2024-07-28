## Web3.py collections

This module providing alternatives to some of the web3's classes

### Installation

Install the package using the following command:

```shell
pip install -U web3-collections
```

### Alternatives

| Class name                                                  | Alternative to |
|-------------------------------------------------------------|:--------------:|
| [**MultiEndpointHTTPProvider**](#multiendpointhttpprovider) |  HTTPProvider  |

#### MultiEndpointHTTPProvider

The constructor gives a list of endpoint URIs. In each http request, it tries to use the `current_endpoint` to fetch
data and if it fails, updates the current endpoint and tries again.

```python
import web3
from web3_collections import MultiEndpointHTTPProvider

endpoint_uris = ['https://rpc.ankr.com/eth', 'https://1rpc.io/eth', 'https://eth.drpc.org', ...]
w3 = web3.Web3(MultiEndpointHTTPProvider(endpoint_uris))
```

By default `auto_update=True` and you don't need to use `update_endpoint` method. But, you can disable auto update and
handle it manually:

```python
w3 = web3.Web3(MultiEndpointHTTPProvider(endpoint_uris, auto_update=False))
try:
    w3.eth.get_block('latest')
except Exception as e:
    print(f'{w3.provider.current_endpoint} got error: {e}')
    w3.provider.update_endpoint()
    print(f'Endpoint updated to {w3.provider.current_endpoint}')
```

Method `MultiEndpointHTTPProvider.sort_endpoints` sorts the endpoints by their latest block number
(most updated will choose as `current_endpoint`):

```python
>>> endpoint_uris = [
...  'https://arbitrum.meowrpc.com',
...  'https://1rpc.io/arb',
...  'https://arbitrum-one-rpc.publicnode.com',
...  'https://arb-pokt.nodies.app'
... ]
>>> w3 = web3.Web3(MultiEndpointHTTPProvider(endpoint_uris))
>>> w3.provider.current_endpoint  # before sorting
'https://arbitrum.meowrpc.com'
>>> w3.provider.sort_endpoints()  # sorting by latest block number
>>> w3.provider.current_endpoint  # after sorting
'https://arbitrum-one-rpc.publicnode.com'
```
