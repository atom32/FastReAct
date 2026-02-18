#!/bin/bash
# Verification Script for P0 Documentation Fixes
# Generated: 2026-02-18
# Usage: cd /Users/xudawei/FastReAct/fastreact-nano && bash ANALYSIS_OUTPUT/documentation/verify_p0_fixes.sh

set -e

echo "================================"
echo "P0 Fixes Verification"
echo "================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

check_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}[PASS]${NC} $2"
        ((PASS_COUNT++))
    else
        echo -e "${RED}[FAIL]${NC} $2"
        ((FAIL_COUNT++))
    fi
}

echo "=== Fix 1: Version Number Synchronization ==="
echo ""

# Check pyproject.toml
PYPROJECT_VERSION=$(grep "^version = " pyproject.toml | grep -o "2\.[0-9]\+\.[0-9]\+")
if [ "$PYPROJECT_VERSION" = "2.1.0" ]; then
    check_result 0 "pyproject.toml version is 2.1.0"
else
    check_result 1 "pyproject.toml version is $PYPROJECT_VERSION (expected 2.1.0)"
fi

# Check __init__.py
INIT_VERSION=$(grep "__version__" src/fastreact/__init__.py | grep -o "2\.[0-9]\+\.[0-9]\+")
if [ "$INIT_VERSION" = "2.1.0" ]; then
    check_result 0 "__init__.py version is 2.1.0"
else
    check_result 1 "__init__.py version is $INIT_VERSION (expected 2.1.0)"
fi

# Check README.md
README_VERSION=$(grep "^\*\*Version\*\*:" README.md | grep -o "2\.[0-9]\+\.[0-9]\+")
if [ "$README_VERSION" = "2.1.0" ]; then
    check_result 0 "README.md version is 2.1.0"
else
    check_result 1 "README.md version is $README_VERSION (expected 2.1.0)"
fi

# Check CLAUDE.md
CLAUDE_VERSION=$(grep "^\*\*Version\*\*:" CLAUDE.md | grep -o "2\.[0-9]\+\.[0-9]\+")
if [ "$CLAUDE_VERSION" = "2.1.0" ]; then
    check_result 0 "CLAUDE.md version is 2.1.0"
else
    check_result 1 "CLAUDE.md version is $CLAUDE_VERSION (expected 2.1.0)"
fi

echo ""
echo "=== Fix 2: Total Line Count Correction ==="
echo ""

# Check total LOC
TOTAL_LOC=$(find src/fastreact -name "*.py" -type f | xargs wc -l | tail -1 | awk '{print $1}')
if [ "$TOTAL_LOC" = "8869" ]; then
    check_result 0 "Total LOC is 8,869"
else
    check_result 1 "Total LOC is $TOTAL_LOC (expected 8,869)"
fi

# Check if README mentions 8,869
if grep -q "8,869" README.md; then
    check_result 0 "README.md mentions 8,869 lines"
else
    check_result 1 "README.md does not mention 8,869 lines"
fi

# Check if old 5,592 is removed
if ! grep -q "5,592" README.md; then
    check_result 0 "README.md does not mention old 5,592 count"
else
    check_result 1 "README.md still mentions old 5,592 count"
fi

echo ""
echo "=== Fix 3: Agent Line Count Correction ==="
echo ""

# Check Agent LOC
AGENT_LOC=$(wc -l < src/fastreact/agent.py)
if [ "$AGENT_LOC" = "944" ]; then
    check_result 0 "Agent LOC is 944"
else
    check_result 1 "Agent LOC is $AGENT_LOC (expected 944)"
fi

# Check if README mentions 944
if grep -q "944 lines" README.md; then
    check_result 0 "README.md mentions 944 lines for Agent"
else
    check_result 1 "README.md does not mention 944 lines for Agent"
fi

# Check if old 595 is removed
if ! grep -q "595 lines" README.md; then
    check_result 0 "README.md does not mention old 595 count"
else
    check_result 1 "README.md still mentions old 595 count"
fi

echo ""
echo "=== Fix 4: Core Line Count ==="
echo ""

# Check Core LOC
CORE_LOC=$(wc -l < src/fastreact/core/react.py)
if [ "$CORE_LOC" = "182" ]; then
    check_result 0 "Core LOC is 182"
else
    check_result 1 "Core LOC is $CORE_LOC (expected 182)"
fi

echo ""
echo "=== Fix 5: Event Protocol Completeness ==="
echo ""

# Count event types in code
EVENT_COUNT=$(grep -E "^\s+[A-Z_]+\s*=\s*\"" src/fastreact/core/events.py | wc -l | xargs)
if [ "$EVENT_COUNT" = "10" ]; then
    check_result 0 "Event types count is 10"
else
    check_result 1 "Event types count is $EVENT_COUNT (expected 10)"
fi

# Check if INTERRUPT is documented
if grep -q "INTERRUPT" README.md; then
    check_result 0 "README.md documents INTERRUPT event"
else
    check_result 1 "README.md does not document INTERRUPT event"
fi

# Check if INTERRUPT exists in code
if grep -q "INTERRUPT.*interrupt" src/fastreact/core/events.py; then
    check_result 0 "INTERRUPT event exists in code"
else
    check_result 1 "INTERRUPT event does not exist in code"
fi

echo ""
echo "=== Summary ==="
echo ""
echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All P0 fixes verified successfully!${NC}"
    exit 0
else
    echo -e "${RED}Some P0 fixes need attention.${NC}"
    exit 1
fi
