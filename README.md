# IcePanel Python Library

[![fern shield](https://img.shields.io/badge/%F0%9F%8C%BF-Built%20with%20Fern-brightgreen)](https://buildwithfern.com?utm_source=github&utm_medium=github&utm_campaign=readme&utm_source=https%3A%2F%2Fgithub.com%2FIcePanel%2Ficepanel-js)

The IcePanel Python library provides convenient access to the IcePanel APIs from Python.

## Table of Contents

- [Installation](#installation)
- [Reference](#reference)
- [Getting Started](#getting-started)
- [Request and Response Types](#request-and-response-types)
- [Exception Handling](#exception-handling)
- [Advanced](#advanced)
  - [Additional Headers](#additional-headers)
  - [Additional Query String Parameters](#additional-query-string-parameters)
  - [Retries](#retries)
  - [Timeouts](#timeouts)
  - [Aborting Requests](#aborting-requests)
  - [Access Raw Response Data](#access-raw-response-data)
  - [Logging](#logging)
- [Contributing](#contributing)

## Installation

```sh
pip install icepanel
```

## Reference

A full reference for this library is available [here](https://github.com/IcePanel/icepanel-py/blob/HEAD/./reference.md).

## Getting Started

Use the following constant to specify the latest version.
```python
from icepanel import IcePanelClient, LandscapeVersion

landscape_id = "YOUR_LANDSCAPE_ID"

client = IcePanelClient(
    api_key="YOUR_API_KEY",
    api_version="v1",
)

response = client.model.request(
    "objects",
    params={
        "landscapeId": landscape_id,
        "versionId": LandscapeVersion,
    },
)
```


## Request and Response Types

The SDK returns response bodies as Python dictionaries when the API responds with JSON. You can also
use `.request_raw(...)` to access the raw response object alongside the parsed payload.

## Exception Handling

When the API returns a non-success status code (4xx or 5xx response), a subclass of the following error
will be thrown.

```python
from icepanel import IcePanelError

try:
    client.model.request("objects", params={"landscapeId": landscape_id})
except IcePanelError as err:
    print(err.status_code)
    print(err)
    print(err.body)
    print(err.raw_response)
```

## Advanced

### Additional Headers

If you would like to send additional headers as part of the request, use the `headers` request option.

```python
from icepanel import IcePanelClient

client = IcePanelClient(
    api_key="YOUR_API_KEY",
    headers={"X-Custom-Header": "custom value"},
)

response = client.model.request(
    "objects",
    params={"landscapeId": landscape_id},
    headers={"X-Custom-Header": "custom value"},
)
```

### Additional Query String Parameters

If you would like to send additional query string parameters as part of the request, use the `queryParams` request option.

```python
response = client.model.request(
    "objects",
    params={"customQueryParamKey": "custom query param value"},
)
```

### Retries

The SDK is instrumented with automatic retries with exponential backoff. A request will be retried as long
as the request is deemed retryable and the number of retry attempts has not grown larger than the configured
retry limit (default: 2).

A request is deemed retryable when any of the following HTTP status codes is returned:

- [408](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/408) (Timeout)
- [429](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429) (Too Many Requests)
- [5XX](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500) (Internal Server Errors)

Use the `maxRetries` request option to configure this behavior.

```python
response = client.model.request(
    "objects",
    params={"landscapeId": landscape_id},
    max_retries=0,  # override max retries at the request level
)
```

### Timeouts

The SDK defaults to a 60 second timeout. Use the `timeoutInSeconds` option to configure this behavior.

```python
response = client.model.request(
    "objects",
    params={"landscapeId": landscape_id},
    timeout=30,  # override timeout to 30s
)
```

### Aborting Requests

Python HTTP clients can be interrupted by cancelling the running task or thread that issued the
request. If you need cooperative cancellation, wrap requests in your own timeout or task management.

### Access Raw Response Data

The SDK provides access to raw response data, including headers, through the `.request_raw()` method.
The `.request_raw()` method returns a tuple with the parsed data and the raw response object.

```python
data, raw_response = client.request_raw(
    "GET",
    "model/objects",
    params={"landscapeId": landscape_id},
)

print(data)
print(raw_response.headers.get("X-My-Header"))
```

### Logging

The Python SDK relies on the standard library `logging` module for request-level logging. If you need
HTTP-level logs, configure logging around `urllib` in your application.

## Contributing

While we value open-source contributions to this SDK, this library is generated programmatically.
Additions made directly to this library would have to be moved over to our generation code,
otherwise they would be overwritten upon the next generated release. Feel free to open a PR as
a proof of concept, but know that we will not be able to merge it as-is. We suggest opening
an issue first to discuss with us!

On the other hand, contributions to the README are always very welcome!
