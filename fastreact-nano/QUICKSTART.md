# FastReAct Nano Quickstart

This is the short path for running the current headless HTTP/SSE service.

```bash
cd /Users/xudawei/FastReAct
mkdir -p .fastreact
cp fastreact-nano/config.pska.example.json .fastreact/config.json
```

Edit `.fastreact/config.json`:

```json
{
  "llm": {
    "model": "deepseek-v4-flash",
    "api_base": "https://api.deepseek.com",
    "api_key": "replace-with-real-key"
  },
  "service": {
    "host": "127.0.0.1",
    "port": 18741,
    "service_token": "replace-with-local-service-token"
  },
  "mcp": {
    "servers": []
  }
}
```

Install backend:

```bash
cd /Users/xudawei/FastReAct/fastreact-nano
python3 -m pip install -e ".[all]"
```

Start:

```bash
cd /Users/xudawei/FastReAct
./start.sh
```

Test:

```bash
export SERVICE_TOKEN='replace-with-local-service-token'

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

Useful checks:

```bash
curl http://127.0.0.1:18741/health
curl http://127.0.0.1:18741/ready -H "X-FastReAct-Service-Token: $SERVICE_TOKEN"
curl http://127.0.0.1:18741/v1/tools
curl http://127.0.0.1:18741/v1/skills
```

Next: [docs/HEADLESS_SERVICE.md](docs/HEADLESS_SERVICE.md).
