# FastReAct Nano - 5-Minute Quick Start

This guide starts the current `fastreact-nano 2.4.2` headless service from this repository checkout.

## 1. Install Dependencies

Backend:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m pip install -e ".[all]"
```

Optional local service console:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano-web
npm install
```

## 2. Create A Config

Use the repository-level config path for local development:

```bash
cd /Users/xudawei/FastReAct
mkdir -p .fastreact
cp fastreact-nano/config.pska.example.json .fastreact/config.json
```

Edit `.fastreact/config.json` and set:

- `llm.model`
- `llm.api_base`
- `llm.api_key` or `llm.api_key_file`
- `service.service_token`
- `service.cors_origins` if the web console origin changes
- `mcp.servers` if you want stdio or HTTP MCP tools

For daemon-only deployments, `~/.fastreact/config.json` is also supported.

## 3. Start The Service

Recommended local start:

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

Explicit config:

```bash
./start.sh /Users/xudawei/FastReAct/.fastreact/config.json
```

Daemon-only:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m fastreact.adapters.http --config /Users/xudawei/FastReAct/.fastreact/config.json
```

Defaults:

```text
Service console: http://127.0.0.1:3000/service
HTTP daemon:     http://127.0.0.1:18741
```

## 4. Check Health And Readiness

```bash
curl http://127.0.0.1:18741/health
```

If `service.service_token` is configured:

```bash
export SERVICE_TOKEN='replace-with-local-service-token'

curl http://127.0.0.1:18741/ready \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
```

## 5. Send A Request

```bash
curl http://127.0.0.1:18741/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "Say hello from FastReAct."}
    ],
    "stream": false
  }'
```

Streaming:

```bash
curl -N http://127.0.0.1:18741/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -H "X-FastReAct-Service-Token: $SERVICE_TOKEN" \
  -d '{
    "messages": [
      {"role": "user", "content": "List your available tools."}
    ],
    "stream": true
  }'
```

## Next Docs

- [README.md](README.md)
- [docs/DOCS_INDEX.md](docs/DOCS_INDEX.md)
- [docs/HEADLESS_SERVICE.md](docs/HEADLESS_SERVICE.md)
- [docs/CONFIG_FILE_LOCATIONS.md](docs/CONFIG_FILE_LOCATIONS.md)
- [docs/PSKA_FASTREACT_PROTOCOL.md](docs/PSKA_FASTREACT_PROTOCOL.md)
