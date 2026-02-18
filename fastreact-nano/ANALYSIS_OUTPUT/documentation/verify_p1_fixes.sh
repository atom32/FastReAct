#!/bin/bash
# Verification Script for P1 Documentation Fixes
# Generated: 2026-02-18
# Usage: cd /Users/xudawei/FastReAct/fastreact-nano && bash ANALYSIS_OUTPUT/documentation/verify_p1_fixes.sh

set -e

echo "================================"
echo "P1 Fixes Verification"
echo "================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
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
}

echo "=== Fix 1: Production Status Clarification ==="
echo ""

# Check if production status has caveats
if grep -q "Status.*Beta" README.md || grep -q "Production Ready.*CLI.*HTTP.*Gateway" README.md; then
    check_result 0 "Production status has caveats or specific adapters"
else
    warn_result "Production status may need clarification"
fi

# Check if Known Issues section exists
if grep -q "## Known Issues" README.md; then
    check_result 0 "Known Issues section exists"
else
    check_result 1 "Known Issues section missing"
fi

# Check if REPL issues are documented
if grep -qi "REPL.*issue\|REPL.*known" README.md; then
    check_result 0 "REPL issues are documented"
else
    check_result 1 "REPL issues not documented"
fi

echo ""
echo "=== Fix 2: Adapter Test Coverage Documentation ==="
echo ""

# Count adapter files
ADAPTER_COUNT=$(ls -1 src/fastreact/adapters/*.py 2>/dev/null | grep -v __pycache__ | grep -v __init__ | wc -l | xargs)
echo "Found $ADAPTER_COUNT adapter files"

# Check if adapter table exists
if grep -q "Adapter.*Status.*Lines" README.md; then
    check_result 0 "Adapter status table exists"
else
    check_result 1 "Adapter status table missing"
fi

# Check if adapter count is documented correctly
if grep -q "8 adapters\|8.*adapter" README.md || grep -q "CLI.*HTTP.*Gateway.*Skills" README.md; then
    check_result 0 "Adapter count is documented (8 or list of adapters)"
else
    warn_result "Adapter count may need clarification"
fi

echo ""
echo "=== Fix 3: Compliance Scores Recalculation ==="
echo ""

# Check if Anti-Entropy score is updated
if grep -q "98\.9/100\|99/100" README.md; then
    check_result 0 "Anti-Entropy score updated to ~99/100"
elif grep -q "100/100.*Core.*182\|100/100.*98\.9" README.md; then
    check_result 0 "Anti-Entropy score has evidence"
else
    warn_result "Anti-Entropy score may need update (currently 182/180)"
fi

# Check if Core 182 lines is mentioned
if grep -q "Core.*182\|182.*lines" README.md; then
    check_result 0 "Core line count of 182 is mentioned"
else
    check_result 1 "Core line count of 182 not found"
fi

echo ""
echo "=== Fix 4: Design Target Explanation ==="
echo ""

# Check if DESIGN.md has size analysis
if [ -f "docs/DESIGN.md" ]; then
    if grep -q "8,869\|8869" docs/DESIGN.md; then
        check_result 0 "DESIGN.md mentions actual line count"
    else
        check_result 1 "DESIGN.md does not mention actual line count"
    fi

    # Check if growth is explained
    if grep -qi "growth\|exceeded\|breakdown" docs/DESIGN.md; then
        check_result 0 "DESIGN.md explains size growth"
    else
        warn_result "DESIGN.md may need size explanation"
    fi
else
    warn_result "docs/DESIGN.md not found"
fi

echo ""
echo "=== Fix 5: Skills Line Count ==="
echo ""

# Check if skills line count is mentioned
if grep -qi "skills.*lines\|skills.*[0-9]" README.md; then
    check_result 0 "Skills line count is mentioned"
else
    warn_result "Skills line count may need documentation"
fi

# Count skill directories
SKILL_COUNT=$(find skills -name "SKILL.md" 2>/dev/null | wc -l | xargs)
echo "Found $SKILL_COUNT skill definitions"

if [ "$SKILL_COUNT" = "5" ]; then
    check_result 0 "5 skills are documented"
else
    warn_result "Found $SKILL_COUNT skills (expected 5)"
fi

echo ""
echo "=== Fix 6: Core Percentage Calculation ==="
echo ""

# Check if core percentage is updated
if grep -q "2\.0%.*Core\|Core.*2\.0%\|2\.05%.*Core\|Core.*2\.05%" README.md; then
    check_result 0 "Core percentage is ~2.0%"
elif grep -q "0\.3%.*Core" README.md; then
    check_result 1 "Core percentage still shows 0.3% (should be ~2.0%)"
else
    warn_result "Core percentage may need update"
fi

echo ""
echo "=== Fix 7: Anti-Entropy Principle ==="
echo ""

# Check if principle mentions ~180 or actual count
if grep -qi "locked at ~180\|currently 182" README.md; then
    check_result 0 "Anti-Entropy principle mentions actual count"
elif grep -qi "locked at 180" README.md; then
    warn_result "Anti-Entropy principle may need 'currently 182' note"
else
    check_result 1 "Anti-Entropy principle not found"
fi

echo ""
echo "=== Summary ==="
echo ""
echo -e "${GREEN}Passed: $PASS_COUNT${NC}"
echo -e "${RED}Failed: $FAIL_COUNT${NC}"
echo -e "${YELLOW}Warnings: Manual review recommended${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}P1 fixes look good!${NC}"
    echo "Review warnings for optional improvements."
    exit 0
else
    echo -e "${RED}Some P1 fixes need attention.${NC}"
    exit 1
fi
