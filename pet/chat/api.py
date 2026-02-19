"""聊天 Agent API 适配层。当前为占位实现，后续可接入 DeepSeek。"""

from __future__ import annotations


class ChatAgentApi:
    """桌宠聊天 API 客户端占位。"""

    def reply(self, user_message: str) -> str:
        _ = user_message
        return "待接入api"
