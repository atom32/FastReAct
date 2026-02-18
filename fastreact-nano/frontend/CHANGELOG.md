# Changelog

All notable changes to FastReAct Nano will be documented in this file.

## [2.3.0] - 2026-02-18 - **The Visual Update**

### 🎉 Major Release - Complete Vue 3 Frontend

This release marks a major milestone in FastReAct Nano's evolution with a modern, professional web interface built with Vue 3, replacing the Streamlit UI.

### ✨ Features

#### Frontend - Vue 3 SPA
- **Chat Interface** (`/chat`): Modern chat UI with real-time WebSocket streaming
  - Message list with auto-scroll
  - Session management sidebar
  - Real-time AgentEvent rendering (THINK, TOOL_CALL, TOOL_RESULT, ERROR)
  - Markdown rendering with syntax highlighting
  - Dark mode support
  - Responsive design (mobile-friendly)

- **Admin Panel** (`/admin`): Complete system administration
  - **Dashboard**: Real-time system metrics (sessions, events, uptime, memory)
  - **Configuration Editor**: Visual LLM, MCP, and Agent settings
  - **Session Manager**: View, monitor, and terminate active sessions
  - **Status Bar**: Connection status, session count, uptime display

- **MCP Tool Marketplace** (`/marketplace`): Tool discovery and installation
  - 12 MCP tools across 8 categories (Filesystem, Database, Development, etc.)
  - Search, filter, and sort capabilities
  - Featured tools section
  - One-click installation with configuration wizard
  - Tool details with ratings, features, and requirements

#### Backend Enhancements
- **CORS Middleware**: Support for frontend on different origins
- **REST API Endpoints**:
  - `GET /api/config` - Get configuration
  - `PUT /api/config` - Update configuration
  - `GET /api/sessions` - List active sessions
  - `DELETE /api/sessions/{id}` - Terminate session
  - `GET /api/tools` - List available tools
  - `GET /api/mcp/servers` - List MCP servers
  - `GET /api/metrics` - System metrics
  - `GET /health` - Health check
- **Static File Serving**: Gateway serves frontend in production mode

#### Component Library
- **MarketplaceCard**: Tool cards with ratings, install/remove buttons
- **Dashboard**: Metric cards, charts, health status panel
- **ConfigEditor**: Tabbed configuration with validation
- **SessionManager**: Table view, event timeline, export functionality
- **EventRenderer**: Universal event display component

### 🔨 Improvements

#### Build System
- **Vite 7.3**: Fast build and hot module replacement
- **Code Splitting**: Separate chunks for vue-vendor, element-plus, routes
- **Tree Shaking**: Optimized bundle sizes
- **Production Build**: ~1.2MB total (300KB gzipped)

#### Performance
- **WebSocket Streaming**: Real-time AgentEvent protocol
- **Lazy Loading**: Route-based code splitting
- **Virtual Scrolling Ready**: For large event lists
- **Caching Strategy**: Browser cache headers for assets

#### Developer Experience
- **TypeScript**: Full type safety across frontend
- **Element Plus**: Professional UI component library
- **Pinia**: Modern state management
- **TailwindCSS v4**: Utility-first styling
- **Vue Router 4**: Client-side routing

### 🐛 Fixes

#### Frontend
- Fixed TypeScript compilation issues with imports
- Fixed icon imports (Robot → Avatar, Server → Monitor)
- Fixed TailwindCSS v4 PostCSS configuration
- Fixed Element Plus icon name conflicts

#### Build
- Fixed Vite build warnings for dynamic imports
- Fixed path resolution for router imports
- Fixed asset loading in production mode

### 📝 Documentation

#### New Documentation
- `frontend/README.md` - Frontend-specific documentation
- `docs/PHASE2_IMPLEMENTATION.md` - Phase 2.1 summary
- `docs/PHASE2_2_SUMMARY.md` - Phase 2.2 summary (AdminUI)
- `docs/PHASE2_3_SUMMARY.md` - Phase 2.3 summary (Marketplace)

#### Updated Documentation
- `README.md` - Added frontend installation and usage
- `CHANGELOG.md` - Comprehensive changelog format
- `CLAUDE.md` - Added frontend development rules

### 📦 Packaging

#### New Files
- `MANIFEST.in` - Include frontend dist assets in Python package
- `release.sh` - Automated release script with frontend build
- `frontend/` - Complete Vue 3 application (2,500+ lines)

#### Build Artifacts
- `frontend/dist/` - Production build (7.6MB)
- `frontend/dist/index.html` - Application entry point
- `frontend/dist/assets/` - JavaScript, CSS, fonts

### 🚀 Deployment

#### Installation
```bash
# Full installation with frontend
pip install "fastreact-nano[all]"

# Install frontend dependencies
cd frontend && npm install

# Development mode
npm run dev  # Frontend (localhost:5173)
python -m fastreact.adapters.gateway  # Backend (localhost:9000)

# Production build
npm run build
python -m fastreact.adapters.gateway  # Serves frontend at / :9000
```

#### Docker
```bash
# Build includes frontend
docker-compose build

# Start all services
docker-compose up -d
```

### 🔄 Migration from Streamlit

**Old Way**:
```bash
streamlit run src/fastreact/adapters/web.py
```

**New Way**:
```bash
# Development
cd frontend && npm run dev  # + backend

# Production
npm run build && python -m fastreact.adapters.gateway
```

### ⚠️ Breaking Changes

- **Streamlit UI Removed**: Streamlit web interface is no longer included
  - Use Vue 3 frontend at `http://localhost:9000` instead
  - Streamlit adapter (`src/fastreact/adapters/web.py`) is deprecated
- **Gateway Changes**: Now serves static frontend files in production mode
- **API Changes**: REST API endpoints added for configuration and metrics

### 🎨 UI/UX

#### Design System
- **Element Plus**: Professional UI components
- **Dark Mode**: Full theme support (light/dark/auto)
- **Responsive**: Mobile, tablet, and desktop layouts
- **Accessibility**: Keyboard navigation, ARIA labels, semantic HTML

#### Color Scheme
- **Primary**: Blue (#409EFF)
- **Success**: Green (#67C23A)
- **Warning**: Orange (#E6A23C)
- **Danger**: Red (#F56C6C)
- **Info**: Gray (#909399)

### 📊 Statistics

#### Code
- **Frontend**: ~2,500 lines of Vue/TypeScript
- **Components**: 12 major components
- **Views**: 4 main views (Chat, Admin, Marketplace, Config)
- **Tools**: 12 MCP tools in marketplace registry

#### Build
- **Bundle Size**: 1.2MB total (300KB gzipped)
- **Build Time**: ~12 seconds
- **Chunks**: 6 (vue-vendor, element-plus, 3 routes, 1 index)

### 🙏 Credits

#### Frontend Stack
- Vue 3.5+ - Progressive JavaScript framework
- Vite 7.3 - Next generation frontend tooling
- Element Plus 2.13 - Vue 3 UI library
- Pinia 3.0 - Vue state management
- Vue Router 4.6 - Official router
- TailwindCSS 4.1 - Utility-first CSS framework

#### Design
- Based on Element Plus design system
- Inspired by AstrBot WebUI architecture
- Color palette from Material Design

### 🔮 Future Plans

#### Phase 2.4 (Optional)
- Performance optimization
- Mobile responsiveness improvements
- Unit testing with Vitest
- E2E testing with Playwright
- Accessibility audit

#### Phase 3.0 (Future)
- Real MCP server installation (npm/npx integration)
- Tool version management
- User ratings and reviews
- Usage analytics dashboard
- Advanced monitoring and alerting

---

## [2.1.0] - 2025-02-16

### Features
- Multi-tenant Feishu bot support
- Enhanced MCP server management
- Docker deployment improvements

## [2.0.0] - 2025-01-XX

### Features
- Event-driven architecture with AgentEvent protocol
- ReActCore with Tool Registry
- MCP integration
- Cortex components (Token Guard, Ghost Map, Safety)
- Skills system with Markdown parsing

## [1.0.0] - 2024-XX-XX

### Initial Release
- Basic ReAct agent implementation
- Core tools (Read, Write, Exec, Edit)
- LiteLLM provider integration
- CLI adapter
