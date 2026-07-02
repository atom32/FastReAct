# Deployment

FastReAct Nano is deployed primarily as a headless HTTP/SSE agentic service.
The local developer stack can also run the optional Next.js service console.

- FastReAct daemon: FastAPI + HTTP/SSE + agent runtime
- Service console: Next.js, optional local operator UI

No external database is required for the current Nano service. Runtime
control-plane data is stored as JSONL under the configured workspace. New
deployments should use `paths.workspaces_root` (default
`~/FastReAct_workspaces`); `paths.gateway_workspace` remains as a legacy
single-workspace override.

## Configuration

For long-running service deployments, prefer an explicit JSON config:

```bash
cd $FASTREACT_REPO
mkdir -p .fastreact
cp fastreact-nano/config.example.json .fastreact/config.json
```

Then start the local stack with:

```bash
./start.sh
```

For daemon-only operation:

```bash
cd $FASTREACT_REPO/fastreact-nano
python3 -m fastreact.adapters.http --config ../.fastreact/config.json
```

When no `--config` is provided, the daemon itself looks for config in this order:

- `~/.fastreact/config.json`
- `./.fastreact/config.json`
- `./config.json`

The root `./start.sh` is intentionally stricter for local product startup: it
reads `.fastreact/config.json` first, then
`~/.fastreact/config.json`, and every startup setting should be declared in that
JSON file.

Important settings:

- `llm.model`: model name passed to LiteLLM.
- `llm.api_base`: OpenAI-compatible provider base URL when needed.
- `llm.api_key` or `llm.api_key_file`: LLM provider key.
- `service.host`: bind host, usually `127.0.0.1` for local PSKA integration.
- `service.port`: daemon port, usually `18741`.
- `service.service_token`: shared secret required by PSKA and operator clients.
- `service.cors_origins`: local console origins allowed by the daemon.
- `web.enabled`, `web.host`, `web.port`: service console startup settings.
- `logs.http`, `logs.web`: local log files for `./start.sh`.
- `pska.enabled`, `pska.archive`, `pska.refresh_config`, `pska.config_file`:
  PSKA linkage and optional generated-config refresh.
- `paths.workspaces_root`: public runtime workspace root, default `~/FastReAct_workspaces`.
- `paths.gateway_workspace`: legacy single-workspace and JSONL store override.
- `mcp.servers`: external MCP servers exposed to the agent.
- `policy`: per-tool, per-tenant, and per-user execution policy.

## Local Development

```bash
cd $FASTREACT_REPO

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

The root `start.sh` script reads startup settings from JSON config, optionally
refreshes the PSKA FastReAct config when `pska.refresh_config=true`, starts the
daemon, waits for `/health`, starts the service console, and waits for
`/service`.

## PSKA-Linked Run

The preferred PSKA-linked local run is:

```bash
cd $FASTREACT_REPO
./start.sh
```

`./start.sh` expects PSKA settings to be declared under the `pska` object in the
same config file. If `pska.refresh_config=true`, it calls:

```text
{pska.archive}/scripts/fastreact-pska-service-config
```

and writes the result to `pska.config_file`. If `pska.refresh_config=false`, the
daemon uses the main config file directly.

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
cd $FASTREACT_REPO/fastreact-nano
python3 -m fastreact.adapters.http --config ../.fastreact/config.json
```

## Health Checks

Public:

- `GET /health`

Authenticated when `service.service_token` is set:

- `GET /ready`
- `GET /v1/tools`
- `GET /v1/skills`
- `GET /v1/policy`

Example:

```bash
SERVICE_TOKEN="replace-with-local-service-token"

curl -fsS http://127.0.0.1:18741/ready \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

## Release Checklist

Before publishing or pushing a release branch:

```bash
cd $FASTREACT_REPO/fastreact-nano
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
