"""The only way this bot talks to the Research System.

Every call carries the bot's scoped service-account token, which the API grants only
`intake:submit` and `intake:read-own`. The bot therefore cannot approve, publish or change
the graph even if it wanted to.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from app.gateway import receipt_settled

logger = logging.getLogger("discord-gateway.api")


class ResearchAPIError(RuntimeError):
    """A failure the gateway can report without exposing the API's internals."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ResearchAPIClient:
    def __init__(self, base_url: str, token: str, timeout_seconds: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=f"{self._base_url}/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=httpx.Timeout(timeout_seconds),
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, **kwargs) -> dict:
        try:
            response = await self._client.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            # The exception text can contain the full URL; the caller gets a safe summary.
            logger.warning(
                "Research API request failed",
                extra={"action": "api.request.failed", "exception_type": type(exc).__qualname__},
            )
            raise ResearchAPIError("Không thể kết nối với API nghiên cứu") from exc
        if response.status_code >= 400:
            logger.warning(
                "Research API refused the request",
                extra={"action": "api.request.refused", "status_code": response.status_code},
            )
            raise ResearchAPIError(
                "API nghiên cứu đã từ chối yêu cầu này", status_code=response.status_code
            )
        return response.json()

    async def create_receipt(self, payload: dict) -> dict:
        return await self._request("POST", "/intake/receipts", json=payload)

    async def attach_document(
        self,
        receipt_id: str,
        *,
        filename: str,
        content: bytes,
        content_type: str,
        external_item_ref: str,
        provider: str | None = None,
    ) -> dict:
        data = {"external_item_ref": external_item_ref}
        if provider:
            data["provider"] = provider
        return await self._request(
            "POST",
            f"/intake/receipts/{receipt_id}/documents",
            files={"file": (filename, content, content_type)},
            data=data,
        )

    async def get_receipt(self, receipt_id: str) -> dict:
        return await self._request("GET", f"/intake/receipts/{receipt_id}")

    async def find_receipt(self, occurrence_ref: str) -> dict:
        """Find a receipt by the Discord message ID that produced it."""

        return await self._request(
            "GET", "/intake/receipts", params={"occurrence_ref": occurrence_ref}
        )

    async def await_receipt(
        self, receipt_id: str, *, interval_seconds: float, attempts: int
    ) -> dict:
        """Poll until every item reaches a terminal state, or the budget runs out.

        Returning the last known state on timeout is deliberate: a slow source should be
        reported as still processing rather than as a failure it did not have.
        """

        receipt = await self.get_receipt(receipt_id)
        for _ in range(max(0, attempts)):
            if receipt_settled(receipt):
                return receipt
            await asyncio.sleep(interval_seconds)
            receipt = await self.get_receipt(receipt_id)
        return receipt
