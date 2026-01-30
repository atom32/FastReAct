# FastReAct Frontend - v0.dev Prompt

## 复制这个 prompt 到 v0.dev

---

Create a modern, professional AI Agent chat interface with real-time event streaming.

## Overall Layout
- Split screen design: Chat (60% left) + Event Panel (40% right)
- Responsive: stack vertically on mobile
- Header with connection status
- Clean, modern aesthetic with smooth animations

## Color Scheme
- Primary: Deep purple/blue gradient (#667eea to #764ba2)
- Background: Light gray (#f5f5f5)
- Surface: White with subtle shadows
- Event colors:
  * Thinking: Blue (#3b82f6)
  * Action: Purple (#8b5cf6)
  * Observation: Green (#10b981)
  * Answer: Orange (#f59e0b)
  * Error: Red (#ef4444)

## Components

### 1. Header Component
Fixed top bar with:
- Logo/title: "FastReAct" (left)
- Connection status indicator (right):
  * Green dot + "Connected" when WebSocket active
  * Red dot + "Disconnected" when inactive
  * Yellow dot + "Thinking..." when processing
- Session ID display (clickable to copy)
- Dark mode toggle button

### 2. Chat Panel (Left Side, 60%)
Vertical flex container with:

**Message Area** (scrollable, flex-1):
- User messages: Right-aligned blue bubbles
- Assistant messages: Left-aligned gray bubbles
- Auto-scroll to latest message
- Timestamp on each message
- Message status indicators (sending/sent/error)

**Input Area** (fixed bottom):
- Text input (multiline, auto-expand)
- Send button (right side)
- Clear button (left side)
- Character counter
- Disable when disconnected

### 3. Event Panel (Right Side, 40%)
Vertical scrollable area with collapsible event cards:

**Event Timeline** (reverse chronological, newest top):
Each event shows:
- Icon based on type (brain, wrench, eye, checkmark)
- Timestamp
- Expandable content
- Execution time (for tool calls)

**Event Types**:
- `thought`: 💭 Thinking process
- `action`: 🔧 Tool call
  * Show tool name
  * Show parameters (collapsible)
  * Show execution time
- `observation`: 📊 Tool result
  * Truncate long results
  * "Show more" expand button
- `answer`: ✅ Final answer
- `error`: ❌ Error message

**Summary Section** (bottom of panel):
- Total thoughts
- Total tool calls
- Execution time
- Iteration count

### 4. Connection Manager
Background service with:
- Auto-connect on load
- Auto-reconnect with backoff (1s, 2s, 5s, 10s)
- Manual reconnect button
- Connection status hooks

## WebSocket Integration

### Endpoint
```
ws://localhost:8080/ws/{session_id}
```

### Message Format (Client → Server)
```json
{
  "type": "message",
  "content": "user message here",
  "timestamp": "2026-01-30T12:00:00Z"
}
```

### Event Format (Server → Client)
```json
{
  "type": "thought" | "action" | "observation" | "answer" | "error",
  "content": "event content",
  "metadata": {
    "iteration": 1,
    "tool_name": "Calculator",
    "duration": 0.5,
    "timestamp": "2026-01-30T12:00:00Z"
  }
}
```

### Final Response Format
```json
{
  "type": "final",
  "content": "final answer here",
  "stats": {
    "iterations": 3,
    "total_time": 5.2
  }
}
```

## Features

### Real-time Features
1. **Streaming Events**: Display events as they arrive
2. **Typing Indicators**: Show "Thinking..." animation
3. **Live Updates**: Update event count and timing
4. **Auto-scroll**: Keep latest event in view

### User Experience
1. **Keyboard Shortcuts**:
   - Enter: Send message
   - Shift+Enter: New line
   - Ctrl/Cmd+K: Clear chat
   - Escape: Close expanded cards

2. **Mobile Optimizations**:
   - Touch-friendly buttons
   - Swipe gestures (optional)
   - Responsive layout

3. **Accessibility**:
   - ARIA labels
   - Keyboard navigation
   - Screen reader support
   - High contrast mode

### Polish
1. **Animations**:
   - Message fade-in (300ms)
   - Event card slide-in (200ms)
   - Status pulse (thinking state)
   - Smooth transitions (200ms)

2. **Feedback**:
   - Send button animation
   - Connection status toast
   - Error message inline
   - Success checkmark

3. **Empty States**:
   - No messages: "Start a conversation..."
   - No events: "Waiting for events..."
   - Disconnected: "Reconnecting..."

## Technical Requirements

### Framework & Libraries
- React 18 with TypeScript
- Tailwind CSS v3
- shadcn/ui components
- React Query / SWR (optional, for state management)

### Key Dependencies
```
- react
- react-dom
- @tailwindcss/forms
- lucide-react (icons)
- date-fns (timestamps)
- clsx / cn (classnames)
```

### Component Structure
```
src/
├── components/
│   ├── Header.tsx
│   ├── ChatPanel.tsx
│   ├── EventPanel.tsx
│   ├── MessageBubble.tsx
│   ├── EventCard.tsx
│   └── ConnectionStatus.tsx
├── hooks/
│   ├── useWebSocket.ts
│   └── useEventStream.ts
├── lib/
│   └── utils.ts
└── App.tsx
```

### State Management
Use React hooks + Context:
```typescript
interface AppState {
  connected: boolean
  messages: Message[]
  events: Event[]
  sessionId: string
}

const AppContext = createContext<AppState>()
```

## WebSocket Hook Example

```typescript
function useWebSocket(url: string) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<Event[]>([])

  useEffect(() => {
    const ws = new WebSocket(url)

    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => {
      const event = JSON.parse(e.data)
      setEvents(prev => [...prev, event])
    }

    return () => ws.close()
  }, [url])

  return { connected, events, send: ws.send.bind(ws) }
}
```

## Deliverables

1. Single-page React application
2. Fully responsive design
3. WebSocket integration working
4. Dark mode toggle
5. Clean, production-ready code
6. TypeScript types included
7. Component comments

---

## Design Reference
Think: ChatGPT meets Claude's artifact panel
Real-time, clean, professional, with detailed event tracing
