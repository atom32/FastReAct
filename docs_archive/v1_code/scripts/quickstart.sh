#!/bin/bash
# FastReAct Quick Start Script

set -e

echo "=================================="
echo "FastReAct Quick Start"
echo "=================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found"
    echo ""
    echo "Please create .env file first:"
    echo "  cp .env.example .env"
    echo "  vim .env  # Add your API key"
    echo ""
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check API key
if [ -z "$API_KEY" ] || [ "$API_KEY" = "your-api-key-here" ]; then
    echo "⚠️  API_KEY not set in .env file"
    echo ""
    echo "Please edit .env and add your API key:"
    echo "  vim .env"
    echo ""
    exit 1
fi

echo "✅ Configuration loaded"
echo ""

# Check if user wants to run specific command
if [ $# -gt 0 ]; then
    # User provided a command
    echo "Running: $@"
    echo ""
    python -m fastreact.cli.main "$@"
else
    # No command provided, show menu
    echo "Choose an option:"
    echo "  1) Interactive chat"
    echo "  2) Run single query"
    echo "  3) Start Gateway server"
    echo "  4) Exit"
    echo ""
    read -p "Enter choice [1-4]: " choice

    case $choice in
        1)
            echo ""
            echo "Starting interactive chat..."
            echo "Type 'quit' or 'exit' to end the conversation"
            echo ""
            python -m fastreact.cli.main chat
            ;;
        2)
            echo ""
            read -p "Enter your query: " query
            echo ""
            python -m fastreact.cli.main run "$query"
            ;;
        3)
            echo ""
            echo "Starting Gateway server..."
            echo "Press Ctrl+C to stop"
            echo ""
            python -m fastreact.cli.main gateway start
            ;;
        4)
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Invalid choice"
            exit 1
            ;;
    esac
fi
