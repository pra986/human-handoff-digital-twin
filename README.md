# Human-Handoff Digital Twin

Personal website and AI digital twin with HMAC-scoped session tokens, an authenticated owner takeover inbox, and grounded resume tools.

## Architecture Overview

The system pairs a public portfolio chat interface with a deterministic policy engine (`DigitalTwinEngine`) that enforces:
1. **HMAC-SHA256 Scoped Session Tokens**: Every visitor session is bound to a signed token (`session_id`, `scope`, `issued_at`) verified in constant time via `hmac.compare_digest`.
2. **Grounded Resume Tooling**: Career history, projects, skills, and availability are served strictly from structured resume records—preventing ungrounded claims or hallucinated credentials.
3. **Authenticated Owner Takeover Inbox**: When a visitor asks to speak directly with the owner, requests custom consulting terms, or triggers a low-confidence / sensitive-topic gate, the conversation enters a `HANDOFF_PENDING` queue accessible only with an authenticated owner key.

## 6-Stage Workflow

1. **Session Issuance**: Issue an HMAC-SHA256 scoped visitor token (`visitor:chat`).
2. **Intent & Guardrail Triage**: Classify visitor query (resume lookup, project deep-dive, or direct owner handoff request).
3. **Grounded Resume Retrieval**: Execute deterministic resume/project lookup tools against verified profile records.
4. **Confidence & Policy Gate**: Evaluate grounding coverage; route ambiguous or high-stakes inquiries to human handoff.
5. **Owner Takeover Inbox**: Persist handoff ticket in the authenticated owner inbox and pause automated replies.
6. **Owner Resolution & Resume**: Owner authenticates (`owner:inbox`), reviews context, and posts a verified human response.

## Data Contract

- `SessionTokenPayload`: `session_id`, `visitor_name`, `scope` (`visitor:chat` | `owner:inbox`), `signature`
- `ResumeFact`: `fact_id`, `category`, `title`, `details`, `tags`
- `TwinQueryRequest`: `session_token`, `message`, `request_human`
- `TwinQueryResponse`: `session_id`, `reply`, `grounded_fact_ids`, `handoff_triggered`, `ticket_id`, `status`
- `HandoffTicket`: `ticket_id`, `session_id`, `visitor_message`, `status` (`OPEN` | `RESOLVED`), `owner_reply`

## Production Controls

- **Constant-Time Token Verification**: Prevents timing side-channel attacks on HMAC session signatures.
- **Role-Separated Scopes**: Visitor tokens cannot read or resolve the owner takeover inbox.
- **No Unverified Claims**: Responses outside grounded resume facts return an explicit fallback or escalate to the owner.
- **Audit-Ready Handoff Tickets**: Every escalation records `ticket_id`, `session_id`, and timestamped owner resolution.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m twin_app.cli
pytest
```

## Attribution

Inspired by and adapted from the Course 2 (AI Coder) C1 project architecture in [ed-donner/avatar](https://github.com/ed-donner/avatar).
