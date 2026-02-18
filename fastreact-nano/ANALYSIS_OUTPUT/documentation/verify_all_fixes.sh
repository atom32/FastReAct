#!/bin/bash
# Comprehensive Verification Script for All Documentation Fixes
# Generated: 2026-02-18
# Usage: cd /Users/xudawei/FastReAct/fastreact-nano && bash ANALYSIS_OUTPUT/documentation/verify_all_fixes.sh

set -e

echo "================================"
echo "Complete Documentation Verification"
echo "================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
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

warn_result() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN_COUNT++))
}

info_result() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo "=== P0 Verifications ==="
echo ""

# Version consistency
PYPROJECT_VERSION=$(grep "^version = " pyproject.toml 2>/dev/null | grep -o "2\.[0-9]\+\.[0-9]\+" || echo "not found")
INIT_VERSION=$(grep "__version__" src/fastreact/__init__.py 2>/dev/null | grep -o "2\.[0-9]\+\.[0-9]\+" || echo "not found")
README_VERSION=$(grep "^\*\*Version\*\*:" README.md 2>/dev/null | grep -o "2\.[0-9]\+\.[0-9]\+" || echo "not found")
CLAUDE_VERSION=$(grep "^\*\*Version\*\*:" CLAUDE.md 2>/dev/null | grep -o "2\.[0-9]\+\.[0-9]\+" || echo "not found")

if [ "$PYPROJECT_VERSION" = "$INIT_VERSION" ] && [ "$INIT_VERSION" = "$README_VERSION" ] && [ "$README_VERSION" = "$CLAUDE_VERSION" ]; then
    check_result 0 "All versions synchronized: $PYPROJECT_VERSION"
else
    check_result 1 "Versions inconsistent: pyproject=$PYPROJECT_VERSION, init=$INIT_VERSION, readme=$README_VERSION, claude=$CLAUDE_VERSION"
fi

# Line counts
TOTAL_LOC=$(find src/fastreact -name "*.py" -type f 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo "0")
if [ "$TOTAL_LOC" = "8869" ]; then
    check_result 0 "Total LOC accurate: 8,869"
else
    check_result 1 "Total LOC is $TOTAL_LOC (expected 8,869)"
fi

AGENT_LOC=$(wc -l < src/fastreact/agent.py 2>/dev/null || echo "0")
CORE_LOC=$(wc -l < src/fastreact/core/react.py 2>/dev/null || echo "0")

if [ "$AGENT_LOC" = "944" ]; then
    check_result 0 "Agent LOC accurate: 944"
else
    check_result 1 "Agent LOC is $AGENT_LOC (expected 944)"
fi

if [ "$CORE_LOC" = "182" ]; then
    check_result 0 "Core LOC accurate: 182"
else
    check_result 1 "Core LOC is $CORE_LOC (expected 182)"
fi

# Event protocol
EVENT_COUNT=$(grep -E "^\s+[A-Z_]+\s*=\s*\"" src/fastreact/core/events.py 2>/dev/null | wc -l | xargs || echo "0")
if [ "$EVENT_COUNT" = "10" ]; then
    check_result 0 "Event types complete: 10"
else
    check_result 1 "Event types count is $EVENT_COUNT (expected 10)"
fi

if grep -q "INTERRUPT" README.md 2>/dev/null; then
    check_result 0 "INTERRUPT event documented"
else
    check_result 1 "INTERRUPT event not documented"
fi

echo ""
echo "=== P1 Verifications ==="
echo ""

# Production status
if grep -q "## Known Issues" README.md 2>/dev/null; then
    check_result 0 "Known Issues section exists"
else
    warn_result "Known Issues section missing"
fi

if grep -qi "REPL.*issue\|REPL.*experimental" README.md 2>/dev/null; then
    check_result 0 "REPL status documented"
else
    warn_result "REPL status may need clarification"
fi

# Adapter documentation
ADAPTER_COUNT=$(ls -1 src/fastreact/adapters/*.py 2>/dev/null | grep -v __pycache__ | grep -v __init__ | wc -l | xargs || echo "0")
info_result "Found $ADAPTER_COUNT adapter files"

if grep -q "Adapter.*Status" README.md 2>/dev/null; then
    check_result 0 "Adapter status table exists"
else
    warn_result "Adapter status table may be missing"
fi

# Compliance scores
if grep -q "98\.9/100\|99/100" README.md 2>/dev/null; then
    check_result 0 "Anti-Entropy score updated"
elif grep -q "Core.*182\|182.*lines" README.md 2>/dev/null; then
    check_result 0 "Core 182 lines mentioned"
else
    warn_result "Compliance scores may need update"
fi

# Skills
SKILL_COUNT=$(find skills -name "SKILL.md" 2>/dev/null | wc -l | xargs || echo "0")
info_result "Found $SKILL_COUNT skill definitions"

# Core percentage
if grep -q "2\.0%.*Core\|Core.*2\.0%\|2\.05%.*Core\|Core.*2\.05%" README.md 2>/dev/null; then
    check_result 0 "Core percentage accurate (~2.0%)"
elif grep -q "0\.3%.*Core" README.md 2>/dev/null; then
    check_result 1 "Core percentage still shows 0.3% (should be ~2.0%)"
else
    warn_result "Core percentage not found"
fi

echo ""
echo "=== P2 Verifications ==="
echo ""

# Cross-layer imports
if grep -q "Modular Layering\|No Penetration" CLAUDE.md 2>/dev/null; then
    check_result 0 "Modular layering documented"
else
    warn_result "Modular layering documentation may be missing"
fi

# GraphRAG disclaimer
if [ -f "MULTITENANT_GRAPHRAG.md" ]; then
    if grep -qi "mock\|reference implementation\|demo" MULTITENANT_GRAPHRAG.md 2>/dev/null; then
        check_result 0 "GraphRAG mock/disclaimer exists"
    else
        warn_result "GraphRAG may need mock implementation disclaimer"
    fi
fi

# Terminology
if grep -q "Ghost Map" README.md 2>/dev/null; then
    warn_result "'Ghost Map' terminology found (should be 'FilesystemMemory')"
else
    check_result 0 "Terminology consistent (no 'Ghost Map')"
fi

# Design target explanation
if [ -f "docs/DESIGN.md" ]; then
    if grep -q "8,869\|8869" docs/DESIGN.md 2>/dev/null; then
        check_result 0 "DESIGN.md mentions actual size"
    else
        warn_result "DESIGN.md may need size update"
    fi
fi

echo ""
echo "=== Overall Statistics ==="
echo ""

info_result "Total Source Files: $(find src/fastreact -name "*.py" | wc -l | xargs)"
info_result "Total Lines: $TOTAL_LOC"
info_result "Core Lines: $CORE_LOC"
info_result "Agent Lines: $AGENT_LOC"
info_result "Adapter Files: $ADAPTER_COUNT"
info_result "Skill Definitions: $SKILL_COUNT"
info_result "Event Types: $EVENT_COUNT"

echo ""
echo "=== Accuracy Assessment ==="
echo ""

# Calculate accuracy
TOTAL_CHECKS=20
ACCURACY=$((PASS_COUNT * 100 / TOTAL_CHECKS))

echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo -e "${YELLOW}Warnings: $WARN_COUNT${NC}"
echo ""
echo "Estimated Documentation Accuracy: ${ACCURANCE}%"

if [ $FAIL_COUNT -eq 0 ] && [ $WARN_COUNT -lt 3 ]; then
    echo ""
    echo -e "${GREEN}✓ Documentation is in excellent shape!${NC}"
    echo "Ready for v2.1.0 release."
    exit 0
elif [ $FAIL_COUNT -eq 0 ]; then
    echo ""
    echo -e "${YELLOW}⚠ Documentation looks good with minor warnings.${NC}"
    echo "Review warnings above for optional improvements."
    exit 0
else
    echo ""
    echo -e "${RED}✗ Documentation needs attention before release.${NC}"
    echo "Please address failed checks above."
    exit 1
fi
