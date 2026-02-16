#!/bin/bash
# FastReAct Nano - Enhanced CLI Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use correct Python
PYTHON_BIN="/usr/local/bin/python3"

# Add src to PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR/src:$PYTHONPATH"

# Run enhanced CLI
"$PYTHON_BIN" -m fastreact.adapters.cli_enhanced
