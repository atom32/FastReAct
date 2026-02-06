# Sprint 5 Testing Guide

Complete guide for testing Sprint 5 auto-reflection capabilities.

---

## Quick Test (No LLM Required)

### Demo 4: Manual Evaluation API

Fastest way to verify TaskEvaluator works:

```bash
python demo_auto_reflection.py
```

**Expected Output**:
```
[TEST 1] Successful execution
  Outcome: success
  Success: True
  Needs Fix: False

[TEST 2] Python traceback
  Outcome: fix
  Success: False
  Needs Fix: True
  Failure Reason: Code error detected
  Suggested Fix: Fix this error: NameError: name 'print' is not defined

[TEST 3] Bash error
  Outcome: fix
  Success: False
  Needs Fix: True
  Failure Reason: Command failed: no such file or directory
  Suggested Fix: Check if the file path is correct and the file exists.
```

---

## Full Integration Test (Requires LLM)

### Option 1: Demo Script with Real LLM

Edit `demo_auto_reflection.py` and uncomment lines in `main()`:

```python
# Uncomment these lines:
if response.lower() == 'y':
    await demo_syntax_error()      # Demo 1: Syntax error
    await demo_bash_error()        # Demo 2: Bash error
    await demo_success_case()      # Demo 3: Success case
```

Run:
```bash
python demo_auto_reflection.py
```

**What to Expect**:
1. Agent tries to write broken Python code
2. TaskEvaluator detects syntax error
3. FollowUpPump auto-generates fix task
4. Agent attempts to fix the error

### Option 2: CLI REPL Test

Interactive testing with live feedback:

```bash
python -m fastreact.cli.unified_repl
```

**Test Scenario 1: Syntax Error**
```
>>> run Write a Python file with syntax error: def hello( print("test")
```

**Expected**:
- Agent attempts to write the file
- Evaluator detects syntax error
- Check with: `/tasks` to see if fix task was generated

**Test Scenario 2: File Not Found**
```
>>> run Read the content of /nonexistent_file_12345.txt
```

**Expected**:
- Command fails with "no such file"
- Evaluator classifies as FIX
- Fix task auto-generated

**Test Scenario 3: Success Case**
```
>>> run echo "Hello, FastReAct!"
```

**Expected**:
- Command succeeds
- No fix tasks generated
- Check with: `/tasks` should show 0 pending

### Option 3: Programmatic Test

Create your own test script:

```python
import asyncio
from fastreact import FastReAct
from fastreact.bootstrap.config_loader import load_config, get_api_key, get_base_url, get_model

async def test():
    config = load_config()
    agent = FastReAct(
        api_key=get_api_key(config),
        base_url=get_base_url(config),
        model=get_model(config),
        config=config,
        enable_bootstrap=True,
    )

    # This will fail
    result = await agent.run_async("ls /nonexistent_directory")

    # Check if fix task was generated
    scheduler = agent.get_task_scheduler()
    status = scheduler.get_status()
    print(f"Pending tasks: {status['total_tasks']}")

asyncio.run(test())
```

---

## Unit Tests (No LLM Required)

### Run Test Suite

```bash
python test_auto_reflection.py
```

**Tests**:
1. Test 1: Command Failure (bash error)
2. Test 2: Python Traceback Detection
3. Test 3: Successful Execution
4. Test 4: Fix Message Generation

**Expected**: All 4 tests PASS

---

## Manual API Testing

Test TaskEvaluator directly:

```python
import asyncio
from fastreact.core import create_evaluator, ToolResult

async def test():
    evaluator = create_evaluator()

    # Test 1: Success
    result = ToolResult(tool_name="echo", result="Hello!")
    eval_result = await evaluator.evaluate(result)
    print(f"Outcome: {eval_result.outcome.value}")  # success

    # Test 2: Error
    result = ToolResult(
        tool_name="python",
        result="Traceback (most recent call last):\nSyntaxError"
    )
    eval_result = await evaluator.evaluate(result)
    print(f"Outcome: {eval_result.outcome.value}")  # fix
    print(f"Needs Fix: {eval_result.needs_fix}")  # True

asyncio.run(test())
```

---

## Verification Checklist

### TaskEvaluator Functionality
- [x] Detects Python tracebacks
- [x] Detects syntax errors
- [x] Detects bash errors (file not found, permission denied)
- [x] Classifies exit codes correctly
- [x] Generates fix suggestions
- [x] Distinguishes FIX vs RETRY

### FollowUpPump Integration
- [x] Auto-evaluation runs after tool execution
- [x] Fix tasks auto-injected with correct priority
- [x] Fix tasks take priority over scheduled tasks
- [x] No false positives on successful execution

### Error Classification
- [x] Code errors → FIX (not retry)
- [x] File not found → FIX (wrong path)
- [x] Permission denied → FIX (needs permission)
- [x] Transient errors → RETRY (can retry)

---

## Debugging

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Evaluator Statistics

```python
evaluator = create_evaluator()
# ... run evaluations ...
stats = evaluator.get_stats()
print(stats)
# {'total_evaluations': 10, 'success_count': 7, 'retry_count': 1, 'fix_count': 2, 'fatal_count': 0}
```

### Inspect Scheduled Tasks

```python
scheduler = agent.get_task_scheduler()
status = scheduler.get_status()
print(f"Total: {status['total_tasks']}")
print(f"Pending: {status['pending_tasks']}")
print(f"Completed: {status['completed_tasks']}")
```

---

## Common Issues

### Issue: No Fix Tasks Generated

**Possible Causes**:
1. Auto-evaluation disabled in config
2. TaskEvaluator not initialized in FollowUpPump
3. Tool execution succeeded (no error)

**Solution**:
```python
config = load_config()
config["reactive_loop"] = {"enabled": True}  # Enable reactive loop
```

### Issue: Wrong Classification (RETRY instead of FIX)

**Possible Causes**:
1. Error pattern not in fix_patterns list
2. Pattern matching failed (case sensitivity)

**Solution**: Check evaluator.py error patterns

### Issue: LLM Not Responding to Fix Tasks

**Possible Causes**:
1. Fix task not injected into message history
2. Fix task has low priority
3. LLM chose to ignore

**Solution**: This is expected behavior - LLM may choose how to respond

---

## Performance Testing

### Benchmark Evaluation Speed

```python
import time
from fastreact.core import create_evaluator, ToolResult

async def benchmark():
    evaluator = create_evaluator()

    # Test 1000 evaluations
    start = time.time()
    for i in range(1000):
        result = ToolResult(tool_name="echo", result=f"Test {i}")
        await evaluator.evaluate(result)

    elapsed = time.time() - start
    print(f"1000 evaluations in {elapsed:.2f}s")
    print(f"Average: {elapsed/1000*1000:.2f}ms per evaluation")

asyncio.run(benchmark())
```

**Expected**: < 1ms per evaluation (hard metrics only)

---

## Next Steps After Testing

1. **Verify Tests Pass**: All 4 tests in test_auto_reflection.py
2. **Try CLI Demo**: Run `/run` with failing command
3. **Check Task Queue**: Use `/tasks` to see generated fix tasks
4. **Review Logs**: Check for [EVALUATOR] warnings
5. **Report Issues**: Document any unexpected behavior

---

## Success Criteria

### Sprint 5 Phase 1 - Testing

- [ ] Unit tests pass (test_auto_reflection.py)
- [ ] Demo 4 runs without errors
- [ ] Manual API testing works
- [ ] Error classification is correct
- [ ] Fix suggestions are generated
- [ ] No false positives on success cases

### Sprint 5 Phase 2 - Future

- [ ] LLM reflection testing
- [ ] Context-aware evaluation
- [ ] Full TOTE loop integration

---

**For questions or issues, see DEVELOPMENT_LOG.md or SPRINT_5_SUMMARY.md**
