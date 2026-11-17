from .engine import DigitalTwinHandoffEngine


def sample_resume_lookup(query: str) -> str:
    if "experience" in query.lower() or "python" in query.lower():
        return "Verified resume fact: 5+ years building Python and AI agent systems."
    raise RuntimeError("Resume tool unavailable for unindexed query")


def run_demo() -> None:
    engine = DigitalTwinHandoffEngine(resume_lookup_fn=sample_resume_lookup)
    conv_id = "conv-demo-001"
    token = engine.issue_session_token(conv_id)
    admin_jwt = engine.issue_admin_jwt(owner_id="pranil")

    engine.send_visitor_message(conv_id, token, "Tell me about your Python experience.")
    engine.send_visitor_message(conv_id, token, "What is your personal phone number?")
    engine.owner_takeover(conv_id, admin_jwt, initial_reply="Hi! Pranil here—happy to chat directly.")

    for msg in engine.poll_messages(conv_id, token):
        print(f"{msg.role_badge} {msg.content}")


if __name__ == "__main__":
    run_demo()
