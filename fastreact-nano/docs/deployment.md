# Deployment

FastReAct Nano is deployed primarily as a headless HTTP/SSE agentic service.
The local developer stack can also run the optional Next.js service console.

- FastReAct daemon: FastAPI + HTTP/SSE + agent runtime
- Service console: Next.js, optional local operator UI

No external database is required for the current Nano service. Runtime
control-plane data is stored as JSONL under `paths.gateway_workspace/.fastreact/`
or `$FASTRACT_GATEWAY_WORKSPACE/.fastreact/`.

## Configuration

For long-running service deployments, prefer an explicit JSON config:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
mkdir -p ~/.fastreact
cp config.example.json ~/.fastreact/config.json
```

Then start with:

```bash
python3 -m fastreact.adapters.http --config ~/.fastreact/config.json
```

When no `--config` is provided, FastReAct looks for config in this order:

- `~/.fastreact/config.json`
- `./.fastreact/config.json`
- `./config.json`

Important settings:

- `llm.model`: model name passed to LiteLLM.
- `llm.api_base`: OpenAI-compatible provider base URL when needed.
- `llm.api_key` or `llm.api_key_file`: LLM provider key.
- `service.host`: bind host, usually `127.0.0.1` for local PSKA integration.
- `service.port`: daemon port, usually `8000`.
- `service.service_token`: shared secret required by PSKA and operator clients.
- `paths.gateway_workspace`: workspace and JSONL store root.
- `mcp.servers`: external MCP servers exposed to the agent.
- `policy`: per-tool, per-tenant, and per-user execution policy.

## Local Development

```bash
cd /Users/xudawei/FastReAct

# backend
cd fastreact-nano
python3 -m pip install -e ".[all]"

# frontend console
cd ../fastreact-nano-web
npm install

# start daemon + console, using PSKA config when available
cd ..
./start.sh
```

The root `start.sh` script refreshes the PSKA FastReAct config when the PSKA
generator exists, starts the daemon, waits for `/health`, starts the service
console, and waits for `/service`.

Useful overrides:

```bash
export PSKA_ARCHIVE="/Users/xudawei/Documents/personal archive"
export PSKA_FASTREACT_CONFIG="$PSKA_ARCHIVE/.pska/fastreact-pska-http.json"
export FASTREACT_SERVICE_HOST="127.0.0.1"
export FASTREACT_SERVICE_PORT="8000"
export WEB_PORT="3000"
```

## PSKA-Linked Run

The preferred PSKA-linked local run is:

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

`./start.sh` expects either:

- `$PSKA_ARCHIVE/scripts/fastreact-pska-service-config`, which generates the
  current PSKA MCP HTTP config; or
- an existing `$PSKA_FASTREACT_CONFIG` file.

The generated config should point FastReAct to the PSKA MCP HTTP endpoint,
usually:

```text
http://127.0.0.1:8765/mcp
```

FastReAct should stay behind a local or private network boundary. PSKA remains
responsible for knowledge ACL and source visibility; FastReAct only enforces
agent tool policy.

## Headless Daemon Only

Use this mode when PSKA or another caller manages its own UI:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http --config ~/.fastreact/config.json
```

## Health Checks

Public:

- `GET /health`

Authenticated when `service.service_token` or `FASTREACT_SERVICE_TOKEN` is set:

- `GET /ready`
- `GET /v1/tools`
- `GET /v1/skills`
- `GET /v1/policy`

Example:

```bash
curl -fsS http://127.0.0.1:8000/ready \
  -H "X-FastReAct-Service-Token: $FASTREACT_SERVICE_TOKEN"
```

## Release Checklist

Before publishing or pushing a release branch:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 run_tests.py quick
python3 run_tests.py integration
python3 run_tests.py release-llm
python3 run_tests.py release-full
```

The release gate includes real LLM smoke tests. It reads `~/api_key.txt` and
writes only non-sensitive timing reports.

Before handing the release to PSKA, verify:

- `/ready` reports the agent and PSKA MCP server as ready.
- `/v1/tools` lists the expected PSKA tools.
- `policy.tenant_rules.pska.tools` denies shell and file mutation tools unless
  there is an explicit operator approval path.
- service token values are not committed, logged in public output, or included
  in release artifacts.
- the config does not reference removed PSKA tool names.
