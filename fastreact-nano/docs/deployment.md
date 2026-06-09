# Deployment

FastReAct Nano runs as two processes:

- backend Gateway: FastAPI + WebSocket + Agent runtime
- frontend console: Next.js

No database is required in Phase 1.2. Runtime control-plane data is stored as JSONL under `$FASTRACT_GATEWAY_WORKSPACE/.fastreact/`.

## Local Development

```bash
cd fastreact-nano
cp .env.example .env

cd ../fastreact-nano-web
cp .env.example .env.local
npm install

cd ..
./fastreact-nano/scripts/dev_full.sh
```

## Production-Style Local Run

```bash
cd fastreact-nano-web
npm run build

cd ..
./fastreact-nano/scripts/start_full.sh
```

## Required Settings

Backend:

- `FASTRACT_MODEL`: model name passed to LiteLLM.
- `FASTRACT_API_KEY` or `OPENAI_API_KEY`: LLM provider key.
- `FASTRACT_GATEWAY_WORKSPACE`: workspace and JSONL store root.
- `GATEWAY_ADMIN_KEY`: admin API key.
- `FASTREACT_ADMIN_API_AUTH`: set `true` to protect control-plane APIs.
- `FASTREACT_CORS_ORIGINS`: comma-separated frontend origins.

Frontend:

- `NEXT_PUBLIC_FASTREACT_GATEWAY_HTTP_URL`
- `NEXT_PUBLIC_FASTREACT_GATEWAY_WS_URL`

## Health Checks

Public:

- `GET /health`
- `GET /api/status`

Control-plane:

- `GET /api/health/dependencies`

The dependency health endpoint reports LLM configuration, store writability, MCP configuration, admin auth status, and frontend environment hints. It does not expose API keys.

## Release Gate

Before pushing a release branch:

```bash
cd fastreact-nano
python3 run_tests.py release-full
```

The release gate includes real LLM smoke tests. It reads `~/api_key.txt`, writes only non-sensitive timing reports, and must pass before `~/Github_PAT.txt` is read for push.
