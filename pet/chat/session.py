"""聊天会话状态管理。"""

from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, Signal

from .api import ChatAgentApi

Role = Literal["pet", "player"]
MessageKind = Literal["text", "image", "rich"]


@dataclass(slots=True)
class ChatMessage:
    role: Role
    kind: MessageKind
    content: str
    timestamp: datetime
    record: str = ""


class ChatSession(QObject):
    """共享聊天会话。支持多视图同步与关闭时清理缓存。"""

    message_added = Signal(object)
    session_cleared = Signal()

    def __init__(self, api: ChatAgentApi | None = None, parent=None):
        super().__init__(parent)
        self._api = api or ChatAgentApi()
        self._messages: list[ChatMessage] = []

    @property
    def messages(self) -> list[ChatMessage]:
        return list(self._messages)

    def _append_player_and_reply(self, kind: MessageKind, content: str, record_text: str):
        clean_content = str(content).strip()
        clean_record = str(record_text).strip()
        if not clean_content and not clean_record:
            return

        now = datetime.now()
        player_message = ChatMessage(
            role="player",
            kind=kind,
            content=clean_content,
            timestamp=now,
            record=clean_record,
        )
        self._messages.append(player_message)
        self.message_added.emit(player_message)

        reply_input = clean_record or clean_content
        pet_reply = ChatMessage(
            role="pet",
            kind="text",
            content=self._api.reply(reply_input),
            timestamp=datetime.now(),
            record=self._api.reply(reply_input),
        )
        self._messages.append(pet_reply)
        self.message_added.emit(pet_reply)

    def send_text(self, text: str):
        clean_text = str(text).strip()
        if not clean_text:
            return
        self._append_player_and_reply("text", clean_text, clean_text)

    def send_image(self, image_path: str):
        clean_path = str(image_path).strip()
        if not clean_path:
            return
        record = f"[图片:{Path(clean_path).name}]"
        self._append_player_and_reply("image", clean_path, record)

    def send_composed(self, display_html: str, record_text: str):
        self._append_player_and_reply("rich", display_html, record_text)

    def clear(self):
        self._messages.clear()
        self.session_cleared.emit()
