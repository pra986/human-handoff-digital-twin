# Architecture — Human-Handoff Digital Twin

## System Overview
The **Human-Handoff Digital Twin** (`twin_app`) provides a stateful, security-hardened conversational runtime where an AI Avatar answers visitor questions grounded strictly in verified resume facts and hands off to the human Owner on escalation.

## Core Components
1. **Models (`twin_app/models.py`)**
   - `SessionToken`: HMAC-SHA256 signed token binding `conversation_id`, `issued_at`, and `expires_at` to prevent cross-thread session hijacking.
   - `ChatMessage`: Immutable message record with `conversation_id`, `role` (`visitor`, `avatar`, `owner`), `role_badge` (`[VISITOR]`, `[AI AVATAR]`, `[HUMAN OWNER]`), `content`, and `timestamp`.
   - `OwnerTakeoverReceipt`: Audit receipt returned when an authenticated owner takes over or replies to a conversation thread.

2. **Engine (`twin_app/engine.py`)**
   - `DigitalTwinHandoffEngine`:
     - **HMAC Session Isolation**: Issues and verifies HMAC-signed `SessionToken`s; rejects mismatched or tampered `conversation_id` tokens.
     - **Admin JWT Verification**: Owner takeover and reply routes require a valid HS256-style signed admin JWT with `role == "owner"` and unexpired `exp`.
     - **Distinct Role Badges**: Every message is tagged with an explicit role badge (`[VISITOR]`, `[AI AVATAR]`, `[HUMAN OWNER]`) so polling clients can distinguish human owner replies from AI avatar responses.
     - **Strict Resume-Fact Abstention**: When the resume/fact retrieval tool fails or returns no grounded match, the engine refuses to fabricate facts and returns a deterministic abstention/escalation notice.

3. **CLI (`twin_app/cli.py`)**
   - Runnable demo entrypoint demonstrating visitor chat, tool-failure abstention, owner JWT takeover, and role-badged message polling.
