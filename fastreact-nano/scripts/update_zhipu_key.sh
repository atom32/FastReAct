#!/bin/bash
# 快速更新智谱 AI API key

echo "=== 更新智谱 AI API Key ==="
echo ""
read -p "请输入你的智谱 API key: " api_key

if [ -z "$api_key" ]; then
    echo "[ERROR] API key 不能为空"
    exit 1
fi

# Update config.json
python3 << EOF
import json

config_path = "$HOME/.fastreact/config.json"

with open(config_path, 'r') as f:
    config = json.load(f)

config['llm']['api_key'] = "$api_key"

with open(config_path, 'w') as f:
    json.dump(config, f, indent=2, ensure_ascii=False)

print("[OK] API key 已更新")
EOF

echo ""
echo "✅ API key 已更新!"
echo ""
echo "重启 HTTP daemon 使配置生效:"
echo "  lsof -ti:18741 | xargs kill -9"
echo "  python3 -m fastreact.adapters.http"
