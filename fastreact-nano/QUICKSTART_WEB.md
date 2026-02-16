# FastReAct Nano - Streamlit Web UI Quickstart

This guide shows you how to run FastReAct Nano with a ChatGPT-like web interface.

## Prerequisites

- Python 3.10+
- pip

## Installation (1 minute)

```bash
# Install with web dependencies
cd /path/to/FastReAct/fastreact-nano
pip install -e ".[web]"

# Set your API key
export FASTRACT_API_KEY=sk-your-api-key-here
export FASTRACT_MODEL=gpt-4o-mini
```

## Start Web UI

```bash
# From project root
streamlit run src/fastreact/adapters/web.py
```

Access at: http://localhost:8501

## Features

### Chat Interface

- Natural language conversation
- Real-time response streaming
- Event visualization (thinking, tool calls, results)
- Message history

### Sidebar Controls

- Model selection
- API configuration
- Temperature adjustment
- Session management
- Clear history

### Capabilities

- Read and write files
- Execute shell commands
- Analyze code
- Answer questions
- Multi-step reasoning

## Example Usage

### File Operations

```
User: What files are in the current directory?

Agent: [Tool Call] execute_shell(command="ls -la")
[Tool Result] total 32
drwxr-xr-x  5 user  staff   160 Feb 16 10:00 .
drwxr-xr-x  10 user  staff  320 Feb 16 09:00 ..
-rw-r--r--  1 user  staff  2048 Feb 16 10:00 README.md
...

The current directory contains:
- README.md (2048 bytes)
- src/ (directory)
```

### Code Analysis

```
User: Analyze the main function in src/main.py

Agent: [Tool Call] read_file(path="src/main.py")
[Tool Result] [file content]

I've analyzed the main function in src/main.py:
[analysis details]
```

### Task Execution

```
User: Create a Python script that prints "Hello World"

Agent: I'll create a Python script for you.

[Tool Call] write_file(path="hello.py", content="...")
[Tool Result] File written: hello.py

Done! I've created hello.py that prints "Hello World"
```

## Configuration

### Environment Variables

Set these before starting:

```bash
# Required
export FASTRACT_API_KEY=sk-your-key-here

# Optional
export FASTRACT_MODEL=gpt-4o-mini
export FASTRACT_API_BASE=https://api.openai.com/v1
export FASTRACT_TEMPERATURE=0.7
export FASTRACT_MAX_TOKENS=4096
```

### Sidebar Settings

You can also configure via the web UI sidebar:

1. **Model**: Change the LLM model
2. **API Base**: Set custom API endpoint
3. **API Key**: Enter your API key
4. **Temperature**: Adjust creativity (0.0 - 2.0)

## Advanced Usage

### Custom Working Directory

By default, works in current directory. To change:

```bash
cd /path/to/your/workspace
streamlit run src/fastreact/adapters/web.py
```

### Session Persistence

Sessions are maintained in browser state:
- Message history persists across reruns
- Session ID tracks conversation
- Use "Clear History" to start fresh

### Multi-turn Conversation

The web UI supports multi-turn conversations:

```
User: List all Python files
Agent: [shows list]
User: Read the first one
Agent: [reads first file]
User: Create a summary
Agent: [creates summary]
```

## Troubleshooting

### Streamlit Not Found

```bash
pip install streamlit
# or
pip install -e ".[web]"
```

### API Key Error

```bash
export FASTRACT_API_KEY=sk-your-key-here
```

Or set in sidebar.

### Port Already in Use

```bash
streamlit run src/fastreact/adapters/web.py --server.port 8502
```

### File Not Found Errors

Make sure you're in the correct directory:

```bash
cd /path/to/FastReAct/fastreact-nano
pwd  # Verify location
```

## Docker Alternative

Prefer Docker? See [QUICKSTART_DOCKER.md](QUICKSTART_DOCKER.md)

```bash
docker compose up -d web
# Access at http://localhost:8501
```

## Next Steps

- Try the example queries in the sidebar
- Read [USAGE.md](USAGE.md) for advanced usage
- Check [CLAUDE.md](CLAUDE.md) for development
- Explore [examples/](../examples/) for demos

## Support

- GitHub: https://github.com/atom32/FastReAct/issues
- Docs: https://github.com/atom32/FastReAct
