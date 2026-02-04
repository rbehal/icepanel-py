from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, Mapping, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from icepanel.errors import IcePanelError


LandscapeVersion = "latest"


RETRY_STATUS_CODES = {408, 429}


def _is_retryable(status_code: int) -> bool:
    return status_code in RETRY_STATUS_CODES or 500 <= status_code <= 599


def _merge_headers(
    base_headers: Mapping[str, str], override: Optional[Mapping[str, str]]
) -> Dict[str, str]:
    merged = dict(base_headers)
    if override:
        merged.update(override)
    return merged


@dataclass
class ClientOptions:
    api_key: Optional[str] = None
    api_version: str = "v1"
    base_url: str = "https://api.icepanel.io"
    timeout: int = 60
    max_retries: int = 2
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    text: str
    url: str

    def json(self) -> Any:
        return json.loads(self.text) if self.text else None


class BaseClient:
    def __init__(self, options: ClientOptions) -> None:
        self._options = options
        default_headers: Dict[str, str] = {
            "User-Agent": "icepanel-python-sdk/0.1.0",
            "Accept": "application/json",
        }
        if options.api_key:
            default_headers["Authorization"] = f"Bearer {options.api_key}"
        self._default_headers = _merge_headers(default_headers, options.headers)

    def _build_url(self, path: str) -> str:
        cleaned = path.lstrip("/")
        return f"{self._options.base_url}/{self._options.api_version}/{cleaned}"

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> Any:
        data, _ = self.request_raw(
            method,
            path,
            params=params,
            json_body=json_body,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )
        return data

    def request_raw(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> tuple[Any, HttpResponse]:
        url = self._build_url(path)
        attempts = (max_retries if max_retries is not None else self._options.max_retries) + 1
        request_headers = _merge_headers(self._default_headers, headers)
        last_error: Optional[Exception] = None

        for attempt in range(1, attempts + 1):
            try:
                response = self._send(
                    method=method,
                    url=url,
                    params=params,
                    json_body=json_body,
                    headers=request_headers,
                    timeout=timeout or self._options.timeout,
                )
            except (urllib_error.URLError, ValueError) as exc:
                last_error = exc
                if attempt >= attempts:
                    raise IcePanelError("Request failed") from exc
                time.sleep(2 ** (attempt - 1))
                continue

            if response.status_code < 400:
                return self._parse_response(response), response

            if _is_retryable(response.status_code) and attempt < attempts:
                time.sleep(2 ** (attempt - 1))
                continue

            raise IcePanelError(
                f"IcePanel API error ({response.status_code})",
                status_code=response.status_code,
                body=self._safe_json(response),
                raw_response=response,
            )

        raise IcePanelError("Request failed", raw_response=last_error)

    @staticmethod
    def _safe_json(response: HttpResponse) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    @staticmethod
    def _parse_response(response: HttpResponse) -> Any:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        if response.text:
            return response.text
        return None

    def _send(
        self,
        *,
        method: str,
        url: str,
        params: Optional[Mapping[str, Any]],
        json_body: Optional[Mapping[str, Any]],
        headers: Mapping[str, str],
        timeout: int,
    ) -> HttpResponse:
        if params:
            query = urllib_parse.urlencode(params, doseq=True)
            url = f"{url}?{query}"
        body = None
        request_headers = dict(headers)
        if json_body is not None:
            body = json.dumps(json_body).encode("utf-8")
            request_headers.setdefault("Content-Type", "application/json")

        request = urllib_request.Request(url, data=body, headers=request_headers, method=method.upper())
        try:
            with urllib_request.urlopen(request, timeout=timeout) as response:
                text = response.read().decode("utf-8")
                return HttpResponse(
                    status_code=response.status,
                    headers=dict(response.headers.items()),
                    text=text,
                    url=response.geturl(),
                )
        except urllib_error.HTTPError as exc:
            text = exc.read().decode("utf-8") if exc.fp else ""
            return HttpResponse(
                status_code=exc.code,
                headers=dict(exc.headers.items()) if exc.headers else {},
                text=text,
                url=exc.geturl(),
            )


class ResourceClient:
    def __init__(self, base: BaseClient, resource: str) -> None:
        self._base = base
        self._resource = resource.strip("/")

    def request(
        self,
        method: str,
        path: str = "",
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> Any:
        full_path = "/".join(part for part in [self._resource, path.strip("/")] if part)
        return self._base.request(
            method,
            full_path,
            params=params,
            json_body=json_body,
            headers=headers,
            timeout=timeout,
            max_retries=max_retries,
        )

    def list(
        self,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        return self.request("GET", params=params, headers=headers)

    def get(
        self,
        resource_id: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        return self.request("GET", resource_id, params=params, headers=headers)

    def create(
        self,
        payload: Mapping[str, Any],
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        return self.request("POST", json_body=payload, headers=headers)

    def update(
        self,
        resource_id: str,
        payload: Mapping[str, Any],
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        return self.request("PATCH", resource_id, json_body=payload, headers=headers)

    def delete(
        self,
        resource_id: str,
        *,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        return self.request("DELETE", resource_id, headers=headers)


class IcePanelClient(BaseClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(ClientOptions(**kwargs))
        self._resources: Dict[str, ResourceClient] = {}

    def _resource(self, name: str) -> ResourceClient:
        if name not in self._resources:
            self._resources[name] = ResourceClient(self, name)
        return self._resources[name]

    @property
    def comments(self) -> ResourceClient:
        return self._resource("comments")

    @property
    def diagrams(self) -> ResourceClient:
        return self._resource("diagrams")

    @property
    def domains(self) -> ResourceClient:
        return self._resource("domains")

    @property
    def drafts(self) -> ResourceClient:
        return self._resource("drafts")

    @property
    def flows(self) -> ResourceClient:
        return self._resource("flows")

    @property
    def landscapes(self) -> ResourceClient:
        return self._resource("landscapes")

    @property
    def organizations(self) -> ResourceClient:
        return self._resource("organizations")

    @property
    def share_links(self) -> ResourceClient:
        return self._resource("share-link")

    @property
    def tags(self) -> ResourceClient:
        return self._resource("tags")

    @property
    def teams(self) -> ResourceClient:
        return self._resource("teams")

    @property
    def versions(self) -> ResourceClient:
        return self._resource("versions")

    @property
    def catalog(self) -> ResourceClient:
        return self._resource("catalog")

    @property
    def model(self) -> ResourceClient:
        return self._resource("model")
