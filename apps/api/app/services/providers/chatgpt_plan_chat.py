"""Trò chuyện có công cụ bằng gói ChatGPT riêng của người đang chat.

Dùng lại giao thức gọi công cụ qua JSON có cấu trúc của nhà cung cấp CLI: tuyến gói ChatGPT
chỉ nhận công cụ function gom trong namespace, nên mô phỏng bằng JSON đơn giản và ổn định hơn.
"""

from typing import Any

from pydantic import SecretStr

from app.core.identity import current_actor_id
from app.services import chatgpt_plan
from app.services.object_storage import DocumentError
from app.services.providers.cli_bridge import CliGraphChatProvider


class PlanGraphChatProvider(CliGraphChatProvider):
    def __init__(
        self,
        *,
        api_key: SecretStr | None = None,
        model: str | None = None,
        user_id: str | None = None,
    ):
        if api_key is not None or model is not None:
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE",
                "The ChatGPT plan uses your connected account, not an API key",
                422,
            )
        # Người đang chat trả quota, kể cả khi tiếp tục cuộc trò chuyện của người khác.
        self.user_id = user_id or current_actor_id()
        self.name = chatgpt_plan.PROVIDER_ID
        self.model = chatgpt_plan.model_for(self.user_id)

    def _ensure_available(self) -> None:
        if not chatgpt_plan.enabled():
            raise DocumentError(
                "CHAT_PROVIDER_UNAVAILABLE", "ChatGPT plan usage is not enabled", 503
            )

    def _complete(self, prompt: str, schema: dict[str, Any], system: str) -> dict[str, Any]:
        return chatgpt_plan.plan_complete(
            self.user_id, prompt=prompt, schema=schema, system=system, schema_name="chat_turn"
        )

    def _clean_output(self, output: dict[str, Any]) -> dict[str, Any]:
        return output
