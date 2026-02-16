# WebSocket Double Connection - React Strict Mode Behavior

**Date**: 2026-02-16
**Status**: EXPLAINED

---

## Phenomenon

**Observation**: WebSocket connects twice in development environment

```
[WebSocket] Setting up connection (mount: abc123)
[WebSocket] Server confirmed connection: session-1
[WebSocket] Cleanup called for mount abc123
[WebSocket] Setting up connection (mount: def456)
[WebSocket] Server confirmed connection: session-2
```

---

## Root Cause

### React 18 Strict Mode

This is **expected behavior** in React 18 Strict Mode (development only).

**What React Does**:
1. **Mount** component → Create first WebSocket connection
2. **Unmount** component → Cleanup connection (tests cleanup logic)
3. **Remount** component → Create second WebSocket connection (this one persists)

**Why React Does This**:
- Tests that components properly handle side effects cleanup
- Ensures no memory leaks from unclosed connections
- Verifies state resets correctly between mounts
- Helps catch bugs early in development

---

## Code Implementation

### Location
`fastreact-nano-web/components/chat/use-fastreact-ws.ts`

### Environment-Aware Logging

```typescript
const isDev = process.env.NODE_ENV === 'development'

// Development-only logging utility
const log = isDev
  ? (...args: any[]) => console.log('[WebSocket]', ...args)
  : () => {}

const logError = (...args: any[]) => console.error('[WebSocket]', ...args)

// In useEffect cleanup:
return () => {
  log(`Cleanup called for mount ${mountId}, readyState:`, ...)
}
```

**Benefits**:
- Logs only appear in development
- Production build has zero logging overhead
- `mountId` helps track which connection is which

---

## Production vs Development

### Development Environment (npm run dev)
```
✅ Double mount happens
✅ Cleanup logic tested
✅ Logs show both connections
✅ Stricter error checking
```

### Production Environment (npm run build && npm start)
```
✅ Single mount only
✅ One WebSocket connection
✅ No logging overhead
✅ Optimized performance
```

---

## How to Verify

### Check if Running in Development

**Browser Console**:
```javascript
// Should show: "development"
console.log(process.env.NODE_ENV)
```

**Network Tab**:
- Look for two WebSocket connections in DevTools
- First one closes immediately
- Second one persists and communicates

---

## Common Concerns

### Q: Is this a bug?
**A**: No, this is intentional React 18 behavior.

### Q: Will this happen in production?
**A**: No, production builds mount components only once.

### Q: Does this waste resources?
**A**: Only in development. Production has no overhead.

### Q: Can I disable it?
**A**: You can remove `<StrictMode>` wrapper, but **not recommended**:
- You lose development-time bug detection
- React team recommends keeping Strict Mode
- Helps catch issues before they reach production

---

## Performance Impact

### Development
- Extra mount/unmount cycle: ~5-10ms
- Extra WebSocket creation: ~10-20ms
- **Total overhead**: ~15-30ms (acceptable for dev)

### Production
- **Zero overhead** - single mount only
- No performance impact
- No duplicate connections

---

## Best Practices

### DO:
- [x] Implement proper cleanup in useEffect return
- [x] Use refs to track connection state
- [x] Test cleanup logic with Strict Mode
- [x] Use environment-aware logging
- [x] Document expected Strict Mode behavior

### DON'T:
- [ ] Disable Strict Mode to "fix" this
- [ ] Remove cleanup logic to avoid seeing double mount
- [ ] Use complex hacks to prevent double mount
- [ ] Log in production without environment checks
- [ ] Panic when seeing duplicate connections in dev

---

## Example Timeline

### Development Mount Sequence

```
Time 0ms:   Component mounts (first time)
            → connectInternal() called
            → WebSocket created

Time 50ms:  WebSocket open
            → Connection confirmed
            → Session ID: abc123

Time 100ms: Strict Mode unmounts
            → Cleanup function called
            → WebSocket closed
            → Connection aborted

Time 150ms: Component remounts (second time)
            → connectInternal() called
            → WebSocket created again

Time 200ms: WebSocket open
            → Connection confirmed
            → Session ID: def456
            → Connection persists (no more unmounts)
```

---

## Code Quality

### Cleanup Implementation

**CORRECT**:
```typescript
useEffect(() => {
  const connect = () => {
    wsRef.current = new WebSocket(url)
    // ... setup handlers
  }

  connect()

  return () => {
    // Proper cleanup
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close()
      wsRef.current = null
    }
  }
}, [])
```

**WRONG**:
```typescript
useEffect(() => {
  const ws = new WebSocket(url)
  // No cleanup - causes memory leak!
}, [])
```

---

## Related Documentation

- [React Strict Mode](https://react.dev/reference/react/StrictMode)
- [React useEffect Cleanup](https://react.dev/reference/react/useEffect#parameters)
- [WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

**Summary**: Double connection is normal in development and indicates proper cleanup implementation. Production builds are unaffected.
