from __future__ import annotations

from typing import Any, Optional


class IcePanelError(Exception):
    """Base exception for IcePanel API errors."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        body: Optional[Any] = None,
        raw_response: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.raw_response = raw_response
