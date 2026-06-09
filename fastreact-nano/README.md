# FastReAct Nano

FastReAct Nano is a single-agent workbench with a stable event stream API, WebSocket Gateway, JSONL control-plane store, task tools, permission approvals, and an Admin console.

The current product boundary is intentionally small: one agent runtime, no database, no OS-level sandbox, and no multi-agent worker platform. Risky tools are controlled by confirmation and audit.

## Quick Start

```bash
cd fastreact-nano
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[all]"

cp .env.example .env
# Edit .env and set FASTRACT_API_KEY or OPENAI_API_KEY.

cd ../fastreact-nano-web
npm install
cp .env.example .env.local

cd ..
./fastreact-nano/scripts/dev_full.sh
```

Open:

- Web console: http://localhost:3000
- Gateway health: http://localhost:9000/health
- Gateway status: http://localhost:9000/api/status

## Configuration

Backend values are read from environment variables, then from `~/.fastreact/config.json`, `./.fastreact/config.json`, or `./config.json` where applicable.

Use [`.env.example`](.env.example) for backend settings:

- `FASTRACT_MODEL`, `FASTRACT_API_BASE`, `FASTRACT_API_KEY`
- `FASTRACT_GATEWAY_WORKSPACE`
- `GATEWAY_HOST`, `GATEWAY_PORT`, `GATEWAY_ADMIN_KEY`
- `FASTREACT_ADMIN_API_AUTH`
- `FASTREACT_CORS_ORIGINS`
- `FASTRACT_MCP_SERVERS`

Use [`../fastreact-nano-web/.env.example`](../fastreact-nano-web/.env.example) for frontend settings:

- `NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL`
- `NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL`
- `NEXT_PUBLIC_FASTREACT_ADMIN_KEY`

Do not put real LLM keys, PATs, or private tokens in frontend environment variables.

## Runtime APIs

Stable Python entrypoint:

```python
async for event in agent.run_event_stream(
    query,
    skills=None,
    session_id=None,
    history=None,
    user_key=None,
):
    ...
```

Stable WebSocket controls:

- `query`
- `control interrupt`
- `list_skills`
- `approve_tool`
- `deny_tool`
- `resume_session`

Admin HTTP APIs include sessions, tasks, audit, traces, tools, config, metrics, and dependency health. Set `FASTREACT_ADMIN_API_AUTH=true` to require `X-Admin-Key`.

## Test Gates

```bash
cd fastreact-nano

python3 -m compileall -q src/fastreact scripts run_tests.py
python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py all
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

`release-llm` reads `~/api_key.txt`, records first-event and final timings, and fails unless the LLM Judge passes. `release-full` chains backend tests, frontend build, production audit, E2E, and the release LLM gate.

`~/Github_PAT.txt` is only used after release gates pass and a push is required.

## Store Maintenance

Control-plane data is stored as JSONL under:

```text
$FASTRACT_GATEWAY_WORKSPACE/.fastreact/
```

Maintenance commands:

```bash
python3 scripts/store_maintenance.py stats
python3 scripts/store_maintenance.py backup
python3 scripts/store_maintenance.py export --output .fastreact/export.json
python3 scripts/store_maintenance.py compact --keep-last 5000
```

`compact` keeps the latest session/task snapshots and trims append-only streams after creating a backup by default.

## Operational Docs

- [Deployment](docs/deployment.md)
- [Architecture](docs/architecture.md)
- [Security](docs/security.md)
