import pytest

from twin_app import DigitalTwinHandoffEngine


def test_cross_thread_conversation_id_isolation():
    engine = DigitalTwinHandoffEngine()
    token_a = engine.issue_session_token("thread-a")
    token_b = engine.issue_session_token("thread-b")

    engine.send_visitor_message("thread-a", token_a, "Hello from A")

    with pytest.raises(PermissionError):
        engine.poll_messages("thread-b", token_a)

    with pytest.raises(PermissionError):
        engine.send_visitor_message("thread-a", token_b, "Hijack attempt")


def test_unauthenticated_admin_takeover_rejected():
    engine = DigitalTwinHandoffEngine()
    engine.issue_session_token("thread-1")

    with pytest.raises(PermissionError):
        engine.owner_takeover("thread-1", admin_jwt=None)

    with pytest.raises(PermissionError):
        engine.owner_takeover("thread-1", admin_jwt="invalid.jwt.token")

    with pytest.raises(PermissionError):
        engine.send_owner_message("thread-1", admin_jwt="bad", text="Spoofed owner")


def test_owner_message_polling_with_distinct_role_badge():
    engine = DigitalTwinHandoffEngine(resume_lookup_fn=lambda q: "Python & FastAPI")
    token = engine.issue_session_token("thread-2")
    admin_jwt = engine.issue_admin_jwt("pranil")

    engine.send_visitor_message("thread-2", token, "What is your stack?")
    engine.owner_takeover("thread-2", admin_jwt, initial_reply="Owner joined the chat.")
    engine.send_owner_message("thread-2", admin_jwt, "Happy to schedule a call.")

    messages = engine.poll_messages("thread-2", token)
    badges = [m.role_badge for m in messages]
    assert badges == ["[VISITOR]", "[AI AVATAR]", "[HUMAN OWNER]", "[HUMAN OWNER]"]
    assert messages[-1].role == "owner"
    assert messages[-1].content == "Happy to schedule a call."


def test_zero_resume_hallucination_on_tool_failure():
    def failing_lookup(_query: str):
        raise ConnectionError("Vector store offline")

    engine = DigitalTwinHandoffEngine(resume_lookup_fn=failing_lookup)
    token = engine.issue_session_token("thread-3")

    reply = engine.send_visitor_message("thread-3", token, "Where did Pranil work?")
    assert reply.abstained is True
    assert reply.role_badge == "[AI AVATAR]"
    assert reply.content == DigitalTwinHandoffEngine.ABSTENTION_TEXT
