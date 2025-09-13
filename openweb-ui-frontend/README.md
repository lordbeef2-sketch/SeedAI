# OpenWebUI Frontend

A modern React + TypeScript frontend for the SeedAI backend, featuring streaming chat, RAG uploads, and unknown words tracking.

## 🚀 Quick Start

### Option 1: Run Both Frontend and Backend (Recommended)

From the project root (`D:\SeedAI\`):

```batch
# Double-click or run in command prompt:
run_both.bat
```

This will start:
- Backend Server on http://localhost:8080
- Frontend Dev Server on http://localhost:5173

### Option 2: Run Separately

**Frontend Only:**
```batch
# Double-click or run:
run_frontend.bat
```

**Backend Only:**
```batch
# Double-click or run:
run_backend.bat
```

### Option 3: Manual Commands

**Frontend:**
```bash
cd openweb-ui-frontend
npm install
npm run dev
```

**Backend:**
```bash
cd open-webui-main2/open-webui/backend
python -m uvicorn "open_webui.main:app" --host 0.0.0.0 --port 8080 --forwarded-allow-ips "*"
```

## ✨ Features

- **Streaming Chat**: Real-time SSE streaming with fallback to non-streaming
- **Model Selection**: Dynamic loading from `/api/models`
- **Memory-First Toggle**: Sends `metadata.memory_first=true`
- **LLM Permission Modal**: Handles permission requests with persistent settings
- **RAG Support**: File uploads to `/api/files`
- **Unknown Words Panel**: Auto-hides on 404, shows word counts
- **Emotions Badges**: Displays emotion metadata under messages
- **Settings Page**: Configurable API base URL and preferences
- **Responsive Design**: Mobile-friendly with collapsible sidebar

## 🔧 Environment Variables

- `VITE_API_BASE_URL`: Backend API URL (default: http://localhost:8080)

## 📡 API Integration

The frontend integrates with these SeedAI backend endpoints:

- `GET /api/models` - Model listing
- `POST /api/chat` - Chat completions (streaming/non-streaming)
- `POST /api/files` - RAG file uploads
- `GET /api/unknown_words` - Unknown words tracking
- `POST /api/unknown_words/ack/{word}` - Mark word as learned

## 🎯 LLM Permission Modal

When the backend requests LLM permission, a modal appears with:
- **Allow Once**: Sets `metadata.llm_permission="once"`
- **Deny**: Sets `metadata.llm_permission="deny"`
- Settings persist per conversation

## 🛠️ Development

```bash
npm run dev      # Start dev server
npm run build    # Production build
npm run preview  # Preview production build
npm run lint     # ESLint check
npm run format   # Prettier format
npm run typecheck # TypeScript check
```

## 🏗️ Technologies

- React 18 + TypeScript
- Vite (build tool)
- TailwindCSS + shadcn/ui
- Zustand (state management)
- React Router (navigation)
- React Markdown (message rendering)
- Lucide React (icons)
- Server-Sent Events (streaming)

## 📱 Responsive Design

- Desktop: Full sidebar layout
- Mobile: Collapsible sidebar with overlay
- Touch-friendly controls and navigation

## 🔄 Error Handling

- Network error toasts
- SSE fallback on connection failure
- Graceful degradation for missing endpoints
- Connection retry with exponential backoff

## 🎨 UI Components

Complete shadcn/ui component library:
- Button, Input, Select, Dialog
- Slider, Switch, Toast, Tabs
- Custom components for chat interface

The frontend is production-ready and fully integrated with the SeedAI backend API specifications!