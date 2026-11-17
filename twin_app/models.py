from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

RoleType = Literal["visitor", "avatar", "owner"]

ROLE_BADGES = {
    "visitor": "[VISITOR]",
    "avatar": "[AI AVATAR]",
    "owner": "[HUMAN OWNER]",
}


@dataclass(frozen=True)
class SessionToken:
    conversation_id: str
    issued_at: int
    expires_at: int
    signature: str


@dataclass(frozen=True)
class ChatMessage:
    conversation_id: str
    role: RoleType
    role_badge: str
    content: str
    abstained: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass(frozen=True)
class OwnerTakeoverReceipt:
    conversation_id: str
    owner_id: str
    status: str
    role_badge: str = "[HUMAN OWNER]"
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
