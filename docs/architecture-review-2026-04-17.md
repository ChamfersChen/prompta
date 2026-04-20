# Prompta Architecture Review (2026-04-17)

## Scope

This review maps the current module boundaries, critical runtime flows, and risk areas that should be stabilized before adding new feature requirements.

## System Overview

- Backend: FastAPI + SQLAlchemy async + PostgreSQL + Redis + MinIO.
- Frontend: Vue 3 + Vite + Pinia + Ant Design Vue.
- Deployment: docker-compose services include API, web, postgres, redis, and minio.

## Backend Module Boundaries

- API layer: `server/routers/*`
  - Endpoint definitions, request parsing, auth dependency wiring.
- Service layer: `src/services/*`
  - Business workflows (chat stream, runs, conversation/thread, prompts/skills).
- Repository layer: `src/repositories/*`
  - DB persistence primitives and query composition.
- Storage models: `src/storage/postgres/models_business.py`
  - Shared domain schema for users, conversations, messages, runs, prompts, skills.

## Frontend Module Boundaries

- App shell and routing: `web/src/main.js`, `web/src/router/index.js`.
- API access layer: `web/src/apis/base.js` and feature API modules.
- State stores: `web/src/stores/*`.
- Feature views/components: `web/src/views/*`, `web/src/components/*`.

## High-Level Dependency Graph

- Router -> Service -> Repository -> SQLAlchemy models -> PostgreSQL.
- Service -> Redis stream / queue for run events and async worker signaling.
- Service -> MinIO for attachment storage.
- Frontend router/store/view -> API layer -> backend routers.

## Critical Runtime Flows

### 1) Auth and request access

- Token verification logic exists in `server/utils/auth_middleware.py`.
- Most route protection is enforced by route-level dependencies (`Depends(get_required_user)`).
- Global `AuthMiddleware` in `server/main.py` does not currently reject unauthenticated API requests by itself.

### 2) Chat and thread lifecycle

- Thread creation/list/update/delete handled by `src/services/conversation_service.py` via `ConversationRepository`.
- LLM chat endpoint is in `server/routers/llm_router.py` and streams responses.
- Message and tool-call persistence are coordinated in `src/services/chat_stream_service.py` and repository methods.

### 3) Agent run and event streaming

- Run creation/cancel/polling paths are in `src/services/agent_run_service.py`.
- SSE flow relies on Redis stream reads and DB status checks.

### 4) Prompt and skill file/tree management

- Prompt and skill operations are mixed in `src/services/prompt_service.py`.
- Metadata in DB and file trees under configured `save_dir` are both used.

## Validated Issues (Confirmed)

### A. Hardcoded user id in LLM chat path

- File: `server/routers/llm_router.py:134`
- Behavior: request metadata sets `"user_id": 1`.
- Context: `get_required_user` dependency is commented out in the same endpoint (`server/routers/llm_router.py:114`).
- Risk: user attribution and access correctness are not guaranteed on this path.

### B. Conversation field naming drift (`llm_id` vs `agent_id`)

- DB schema uses `Conversation.llm_id` (`src/storage/postgres/models_business.py:228`).
- Legacy agent-based methods remain in conversation service/repository:
  - `src/services/conversation_service.py:153`
  - `src/repositories/conversation_repository.py:256`
- Risk: code paths using `conv.agent_id` can fail at runtime because model field is `llm_id`.

### C. Undefined symbols in service modules (runtime break risk)

- `src/services/agent_run_service.py`
  - Missing active imports for `AgentRunRepository`, `TERMINAL_RUN_STATUSES`, `agent_manager`.
- `src/services/chat_stream_service.py`
  - Missing active imports for `AgentConfigRepository`, `agent_manager`.
  - Additional undefined variables (`question`, `operation`, `approved`) in current code.
- `src/services/conversation_service.py`
  - Uses `agent_manager` without import.
- Validation: `ruff check` reports multiple `F821 Undefined name` errors across these files.

### D. Prompt service unresolved dependencies

- File: `src/services/prompt_service.py`
- Active code references `SkillRepository`, `get_skill_or_raise`, and `get_mcp_server_names` without import/definition.
- Also includes a type mismatch path:
  - `get_prompt_or_raise(db, id: int)` is called from `get_skill_tree(db, slug: str)`.
- Risk: skill management and dependency operations can fail during execution.

### E. Router comment and mounted prefix mismatch

- File: `server/routers/__init__.py:21`
- Comment says `llm` routes mount as `/api/system/tools/*`, but router prefix is `/llm`.
- Risk: maintenance confusion and incorrect assumptions during changes.

### F. Frontend route guard policy may block future UX

- File: `web/src/router/index.js:188`
- Behavior: logged-in non-admin users are forced to `/market`.
- Risk: future user journeys may be constrained unless this policy is intentional and documented.

## Priority Hardening Plan

1. Restore safe auth behavior on chat endpoints.
   - Re-enable required user dependency where needed.
   - Remove hardcoded `user_id` and use actual authenticated user id.
2. Unify conversation identity terms.
   - Choose canonical field name (`llm_id` recommended, aligns with DB).
   - Remove/replace legacy `agent_id` paths in conversation service/repository.
3. Fix undefined service symbols.
   - Re-enable/import missing repositories and managers.
   - Resolve undefined local variables in stream/resume logic.
4. Split or clean prompt/skill service dependencies.
   - Restore missing imports and helper functions, or split skill logic into dedicated service.
5. Add targeted integration checks.
   - Login -> thread create/list -> chat stream -> run events -> history retrieval.

## Suggested Change-Safe Baseline

- Create a short domain glossary mapping `agent`, `llm`, `thread`, `run`, and `skill`.
- Freeze API contract snapshots for current frontend calls before refactor.
- Add minimal tests for the critical flows listed above to detect regressions during requirement work.
