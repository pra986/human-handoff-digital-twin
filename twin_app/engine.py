import base64
import hashlib
import hmac
import json
import time
from typing import Callable, Dict, List, Optional

from .models import ROLE_BADGES, ChatMessage, OwnerTakeoverReceipt, SessionToken


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


class DigitalTwinHandoffEngine:
    """Enforces HMAC session isolation, admin JWT owner takeover, role badges, and resume-fact abstention."""

    ABSTENTION_TEXT = (
        "Unable to verify resume facts because the retrieval tool is unavailable. "
        "I will not guess or fabricate details; please wait for the human owner."
    )

    def __init__(
        self,
        session_secret: str = "dev-session-secret",
        admin_jwt_secret: str = "dev-admin-jwt-secret",
        resume_lookup_fn: Optional[Callable[[str], Optional[str]]] = None,
    ) -> None:
        self._session_secret = session_secret.encode("utf-8")
        self._admin_jwt_secret = admin_jwt_secret.encode("utf-8")
        self._resume_lookup_fn = resume_lookup_fn
        self._threads: Dict[str, List[ChatMessage]] = {}
        self._owner_active: Dict[str, bool] = {}

    def _sign_session(self, conversation_id: str, issued_at: int, expires_at: int) -> str:
        payload = f"{conversation_id}:{issued_at}:{expires_at}".encode("utf-8")
        return hmac.new(self._session_secret, payload, hashlib.sha256).hexdigest()

    def issue_session_token(self, conversation_id: str, ttl_seconds: int = 3600) -> SessionToken:
        now = int(time.time())
        expires_at = now + ttl_seconds
        sig = self._sign_session(conversation_id, now, expires_at)
        self._threads.setdefault(conversation_id, [])
        return SessionToken(
            conversation_id=conversation_id,
            issued_at=now,
            expires_at=expires_at,
            signature=sig,
        )

    def verify_session_token(self, token: SessionToken, expected_conversation_id: str) -> None:
        if token.conversation_id != expected_conversation_id:
            raise PermissionError("Cross-thread access denied: conversation_id mismatch.")
        if int(time.time()) > token.expires_at:
            raise PermissionError("Session token expired.")
        expected_sig = self._sign_session(
            token.conversation_id, token.issued_at, token.expires_at
        )
        if not hmac.compare_digest(token.signature, expected_sig):
            raise PermissionError("Invalid session token signature.")

    def issue_admin_jwt(self, owner_id: str, ttl_seconds: int = 3600) -> str:
        header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
        now = int(time.time())
        payload = _b64url_encode(
            json.dumps({"sub": owner_id, "role": "owner", "iat": now, "exp": now + ttl_seconds}).encode("utf-8")
        )
        signing_input = f"{header}.{payload}".encode("utf-8")
        sig = _b64url_encode(hmac.new(self._admin_jwt_secret, signing_input, hashlib.sha256).digest())
        return f"{header}.{payload}.{sig}"

    def verify_admin_jwt(self, jwt_token: Optional[str]) -> dict:
        if not jwt_token or jwt_token.count(".") != 2:
            raise PermissionError("Missing or malformed admin JWT.")
        header_b64, payload_b64, sig_b64 = jwt_token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        expected_sig = _b64url_encode(
            hmac.new(self._admin_jwt_secret, signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig_b64, expected_sig):
            raise PermissionError("Invalid admin JWT signature.")
        claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        if claims.get("role") != "owner":
            raise PermissionError("Insufficient role for owner takeover.")
        if int(time.time()) > int(claims.get("exp", 0)):
            raise PermissionError("Admin JWT expired.")
        return claims

    def send_visitor_message(
        self, conversation_id: str, token: SessionToken, text: str
    ) -> ChatMessage:
        self.verify_session_token(token, conversation_id)
        thread = self._threads.setdefault(conversation_id, [])
        visitor_msg = ChatMessage(
            conversation_id=conversation_id,
            role="visitor",
            role_badge=ROLE_BADGES["visitor"],
            content=text,
        )
        thread.append(visitor_msg)

        if self._owner_active.get(conversation_id):
            return visitor_msg

        try:
            fact = self._resume_lookup_fn(text) if self._resume_lookup_fn else None
        except Exception:
            fact = None

        if not fact:
            avatar_msg = ChatMessage(
                conversation_id=conversation_id,
                role="avatar",
                role_badge=ROLE_BADGES["avatar"],
                content=self.ABSTENTION_TEXT,
                abstained=True,
            )
        else:
            avatar_msg = ChatMessage(
                conversation_id=conversation_id,
                role="avatar",
                role_badge=ROLE_BADGES["avatar"],
                content=fact,
                abstained=False,
            )
        thread.append(avatar_msg)
        return avatar_msg

    def owner_takeover(
        self, conversation_id: str, admin_jwt: Optional[str], initial_reply: Optional[str] = None
    ) -> OwnerTakeoverReceipt:
        claims = self.verify_admin_jwt(admin_jwt)
        self._owner_active[conversation_id] = True
        thread = self._threads.setdefault(conversation_id, [])
        if initial_reply:
            thread.append(
                ChatMessage(
                    conversation_id=conversation_id,
                    role="owner",
                    role_badge=ROLE_BADGES["owner"],
                    content=initial_reply,
                )
            )
        return OwnerTakeoverReceipt(
            conversation_id=conversation_id,
            owner_id=str(claims["sub"]),
            status="taken_over",
        )

    def send_owner_message(
        self, conversation_id: str, admin_jwt: Optional[str], text: str
    ) -> ChatMessage:
        self.verify_admin_jwt(admin_jwt)
        self._owner_active[conversation_id] = True
        thread = self._threads.setdefault(conversation_id, [])
        msg = ChatMessage(
            conversation_id=conversation_id,
            role="owner",
            role_badge=ROLE_BADGES["owner"],
            content=text,
        )
        thread.append(msg)
        return msg

    def poll_messages(self, conversation_id: str, token: SessionToken) -> List[ChatMessage]:
        self.verify_session_token(token, conversation_id)
        return list(self._threads.get(conversation_id, []))
