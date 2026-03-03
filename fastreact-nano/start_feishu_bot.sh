#!/bin/bash
# FastReAct Nano - Feishu Bot Launcher

# Load config from ~/.fastreact/config.json
CONFIG_FILE="$HOME/.fastreact/config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "[ERROR] Config file not found: $CONFIG_FILE"
    exit 1
fi

# Extract values using Python
export FEISHU_APP_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu']['app_id'])")
export FEISHU_APP_SECRET=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu']['app_secret'])")
export FEISHU_CONNECTION_MODE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu']['connection_mode'])")
export FEISHU_MULTITENANT=$(python3 -c "import json; print(str(json.load(open('$CONFIG_FILE'))['feishu']['enable_multitenant']).lower())")
export FEISHU_AUTO_RECONNECT=$(python3 -c "import json; print(str(json.load(open('$CONFIG_FILE'))['feishu']['auto_reconnect']).lower())")
export FEISHU_LOG_LEVEL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu']['log_level'])")
export FEISHU_BASE_WORKSPACE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['feishu']['base_workspace'])")

# LLM config
export FASTRACT_MODEL=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['llm']['model'])")
export FASTRACT_API_BASE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['llm']['api_base'])")
export FASTRACT_API_KEY=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['llm']['api_key'])")
export FASTRACT_TEMPERATURE=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['llm']['temperature'])")
export FASTRACT_MAX_TOKENS=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['llm']['max_tokens'])")

echo "[INFO] Starting Feishu bot with config from $CONFIG_FILE"
echo "[INFO] App ID: $FEISHU_APP_ID"
echo "[INFO] Model: $FASTRACT_MODEL"
echo "[INFO] Multi-tenant: $FEISHU_MULTITENANT"
echo "[INFO] Workspace: $FEISHU_BASE_WORKSPACE"
echo ""

# Run the bot
cd fastreact-nano
python3 examples/feishu_sdk_bot.py
