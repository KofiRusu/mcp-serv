# ChatOS Sandbox UI

A modern Cursor-style coding sandbox built with Next.js and Monaco Editor, designed to work with the ChatOS FastAPI backend.

## Features

- **File Explorer**: Browse, create, delete, and manage files in the ChatOS sandbox
- **Monaco Editor**: Professional code editing with syntax highlighting, minimap, and ChatOS theme
- **Python Execution**: Run Python files and see output in real-time
- **AI Assistant**: Integrated chat with support for /swarm, /code, /research, and /deepthinking commands
- **Model Selection**: Choose between council mode or individual models

## Prerequisites

- Node.js 18+ 
- ChatOS backend running on port 8000

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Open http://localhost:3000
```

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running with ChatOS

1. Start the ChatOS backend:
   ```bash
   cd ~/ChatOS-0.1
   ./run.sh
   ```

2. In a new terminal, start the sandbox UI:
   ```bash
   cd ~/ChatOS-0.1/sandbox-ui
   npm run dev
   ```

3. Open http://localhost:3000 in your browser

## Tech Stack

- **Framework**: Next.js 15 with App Router
- **Editor**: Monaco Editor (@monaco-editor/react)
- **Styling**: Tailwind CSS with ChatOS theme
- **Icons**: Lucide React
- **API**: Connects to ChatOS FastAPI backend

## Keyboard Shortcuts

- `Ctrl/Cmd + S`: Save current file
- Standard Monaco Editor shortcuts apply

## Project Structure

```
sandbox-ui/
├── src/
│   ├── app/
│   │   ├── globals.css      # ChatOS theme
│   │   ├── layout.tsx       # Root layout
│   │   └── page.tsx         # Main page
│   ├── components/
│   │   ├── ai-chat.tsx      # AI chat panel
│   │   ├── code-editor.tsx  # Monaco editor wrapper
│   │   ├── editor-interface.tsx  # Main layout
│   │   ├── file-tree.tsx    # File explorer
│   │   ├── output-panel.tsx # Execution output
│   │   └── ui/              # UI components
│   └── lib/
│       ├── api.ts           # API client
│       └── utils.ts         # Utilities
├── .env.local               # Environment config
└── package.json
```
