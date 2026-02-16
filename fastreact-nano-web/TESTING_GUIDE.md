# Testing Guide - Non-Blocking Chat & Duplicate Message Fix

**Date**: 2026-02-16
**Status**: READY FOR TESTING

---

## Pre-Test Checklist

- [ ] Gateway restarted (PID 29313)
- [ ] Next.js dev server running (PID 26016)
- [ ] Browser ready for testing
- [ ] Implementation completed (all 3 files modified)

---

## Test Scenarios

### Test 1: Single Message - No Duplicates

**Objective**: Verify user messages appear only once

**Steps**:
1. Open browser to `http://localhost:3000`
2. Refresh page (Cmd+Shift+R) to clear cache
3. Type "Hello, test message" in input
4. Click Send button

**Expected Results**:
- [ ] Only ONE "Hello, test message" bubble appears
- [ ] Assistant placeholder appears below it
- [ ] Input field remains enabled
- [ ] Send button remains enabled
- [ ] No loading spinner anywhere

**If Failed**:
- Check browser console for errors
- Verify Gateway is running (should see WebSocket connection)
- Check if backend echo was properly disabled

---

### Test 2: Non-Blocking Input

**Objective**: Verify input field never gets blocked

**Steps**:
1. Send first message: "What is 2+2?"
2. IMMEDIATELY send second message: "What is 3+3?"
3. IMMEDIATELY send third message: "What is 4+4?"

**Expected Results**:
- [ ] All 3 user messages appear in order
- [ ] Input field was NEVER disabled
- [ ] Send button was NEVER disabled
- [ ] Can continue typing while assistant processes
- [ ] No loading spinners appear

**Backend Behavior**:
- Message 1: Treated as query (starts new execution)
- Message 2: Treated as steering (added to current execution)
- Message 3: Treated as steering (added to current execution)

**If Failed**:
- Check if `isLoading` was properly removed from ChatInput
- Check if `disabled={!value.trim()}` is correct (should be only condition)

---

### Test 3: Rapid Fire Messages

**Objective**: Stress test the non-blocking UI

**Steps**:
1. Prepare 5 different messages in clipboard/notepad
2. Paste and send each message as quickly as possible
3. Try to send all 5 within 5 seconds

**Expected Results**:
- [ ] All 5 user messages appear
- [ ] 5 assistant placeholders appear
- [ ] Input never blocks or freezes
- [ ] No duplicate user messages
- [ ] Order is preserved

**If Failed**:
- Check browser performance (may need to wait for first response)
- Verify WebSocket message queue is working

---

### Test 4: Interrupt Functionality

**Objective**: Verify "stop" command works with non-blocking UI

**Steps**:
1. Send long task: "Write a 500-word essay about AI"
2. IMMEDIATELY send: "stop"
3. Wait for response

**Expected Results**:
- [ ] "Write a 500-word essay..." appears
- [ ] "stop" appears immediately after
- [ ] Assistant message shows interrupted status
- [ ] Can send new query right away
- [ ] Input remains enabled throughout

**If Failed**:
- Check if interrupt logic still works after removing isLoading
- Verify Gateway processes "stop" command correctly

---

### Test 5: Steering Context

**Objective**: Verify adding context to running task

**Steps**:
1. Send: "Analyze this file"
2. IMMEDIATELY send: "Focus on performance issues"
3. Wait for completion

**Expected Results**:
- [ ] Both messages appear
- [ ] Only ONE assistant response (not two separate ones)
- [ ] Response incorporates both messages
- [ ] Input remains enabled

**If Failed**:
- Check if steering logic works without isLoading blocking

---

### Test 6: Status Labels Still Work

**Objective**: Verify status labels still appear (without spinner)

**Steps**:
1. Send: "What is the capital of France?"
2. Watch status area above input field

**Expected Results**:
- [ ] Status label appears: "Thinking..."
- [ ] Status changes to "Processing..." during tool calls
- [ ] Status clears on session_end
- [ ] NO loading spinner (Loader2 component)
- [ ] Status badge is present but static (not animating)

**If Failed**:
- Check if statusLabel prop is still passed correctly
- Verify status update logic in onEventCallback

---

## Debugging Commands

### Check Gateway Logs
```bash
tail -f /tmp/fastreact-gateway.log
```

### Check WebSocket Messages
1. Open browser DevTools (F12)
2. Go to Network tab
3. Filter by WS (WebSocket)
4. Click on ws://localhost:3000/... connection
5. View Messages tab to see protocol

### Check React State
1. Install React DevTools extension
2. Inspect ChatInterface component
3. Verify `isLoading` state doesn't exist
4. Verify `messages` array has correct structure

### Restart Services
```bash
# Restart Gateway
cd /Users/xudawei/FastReAct/fastreact-nano
pkill -f "fastreact.adapters.gateway"
python3 -m fastreact.adapters.gateway > /tmp/fastreact-gateway.log 2>&1 &

# Restart Next.js (should auto-reload)
# If not, run:
cd /Users/xudawei/FastReAct/fastreact-nano-web
npm run dev
```

---

## Success Criteria

All tests pass when:
- [ ] No duplicate user messages
- [ ] Input never blocks (always enabled when has text)
- [ ] No loading spinners
- [ ] Status labels still work
- [ ] Interrupt and steering features work
- [ ] Multiple messages can be sent rapidly
- [ ] TypeScript compilation passes (already verified)

---

## Known Issues & Workarounds

### Issue: WebSocket Reconnection
**Symptom**: Messages don't send after period of inactivity
**Fix**: Refresh page to reconnect WebSocket

### Issue: Gateway Not Responding
**Symptom**: Messages sent but no response
**Fix**: Check Gateway logs, restart if crashed

### Issue: Browser Cache
**Symptom**: Old JavaScript code still running
**Fix**: Hard refresh (Cmd+Shift+R on Mac, Ctrl+Shift+R on Windows)

---

## Test Results Template

After testing, update this section:

**Test 1 (Single Message)**: PASS / FAIL
**Test 2 (Non-Blocking)**: PASS / FAIL
**Test 3 (Rapid Fire)**: PASS / FAIL
**Test 4 (Interrupt)**: PASS / FAIL
**Test 5 (Steering)**: PASS / FAIL
**Test 6 (Status Labels)**: PASS / FAIL

**Overall**: PASS / FAIL

**Notes**:
- (Add any issues or observations here)

---

## Next Steps After Testing

If All Tests Pass:
1. Commit changes with message: `fix: remove duplicate messages and input blocking`
2. Update CHANGELOG.md
3. Close related issue/feature request

If Tests Fail:
1. Document failure in Test Results section
2. Check logs for errors
3. Refer to Rollback Plan in IMPLEMENTATION_SUMMARY.md
4. Fix issues and retest

---

**Happy Testing!** (This is the only emoji allowed here)
