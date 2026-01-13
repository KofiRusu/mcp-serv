/**
 * API Client Stub
 * 
 * Placeholder for the ChatOS API client.
 */

export interface ChatResponse {
  id: string
  model: string
  response: string
  created: number
  answer?: string
  chosen_model?: string
}

export interface ModelInfo {
  id: string
  name: string
  description?: string
  isDefault?: boolean
  provider?: string
}

export interface StreamEvent {
  type: 'token' | 'done' | 'error' | 'metadata'
  content?: string
  text?: string
  error?: string
  message?: string
  model?: string
  answer?: string
  chosen_model?: string
}

export interface VSCodeStatus {
  running: boolean
  url?: string
  port?: number
  workspace?: string
  error?: string
}

export interface ProjectInfo {
  id: string
  is_git?: boolean
  exists?: boolean
  name: string
  path: string
  description?: string
}

export interface FileTreeResponse {
  files: { name: string; path: string; type: 'file' | 'directory' }[]
  root?: FileInfo
}

export interface FileInfo {
  name: string
  path: string
  type: 'file' | 'directory'
  is_directory?: boolean
  size?: number
  modified?: string
  children?: FileInfo[]
}

export interface ExecutionResult {
  success: boolean
  output: string
  stdout?: string
  stderr?: string
  error?: string
  exitCode?: number
  exit_code?: number
  duration?: number
  execution_time?: number
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Send a chat message to the API
 */
export interface ChatRequest {
  message: string
  mode?: string
  use_rag?: boolean
  session_id?: string
  model_id?: string
  conversation_id?: string
}

export async function sendChatMessage(
  messageOrRequest: string | ChatRequest,
  model?: string,
  conversationId?: string
): Promise<ChatResponse> {
  try {
    let body: Record<string, unknown>
    if (typeof messageOrRequest === 'string') {
      body = {
        message: messageOrRequest,
        model: model || 'default',
        conversation_id: conversationId,
      }
    } else {
      body = {
        message: messageOrRequest.message,
        model: messageOrRequest.model_id || model || 'default',
        mode: messageOrRequest.mode,
        use_rag: messageOrRequest.use_rag,
        session_id: messageOrRequest.session_id,
        conversation_id: messageOrRequest.conversation_id || conversationId,
      }
    }
    
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Chat API error:', error)
    return {
      id: Date.now().toString(),
      model: model || 'default',
      response: 'Sorry, the chat service is currently unavailable. Please try again later.',
      created: Date.now(),
    }
  }
}

export interface StreamChatRequest {
  message: string
  session_id?: string
  model_id?: string
}

/**
 * Stream a chat message from the API (callback-based)
 */
export async function streamChatMessage(
  request: string | StreamChatRequest,
  callback: (event: StreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const req: StreamChatRequest = typeof request === 'string' 
    ? { message: request } 
    : request
    
  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: req.message,
        model: req.model_id || 'default',
        session_id: req.session_id,
      }),
      signal,
    })
    
    if (!response.ok) {
      callback({ type: 'error', error: `API error: ${response.status}` })
      return
    }
    
    const reader = response.body?.getReader()
    if (!reader) {
      callback({ type: 'error', error: 'No response body' })
      return
    }
    
    // Send metadata event with model info
    callback({ type: 'metadata', model: req.model_id || 'default' })
    
    const decoder = new TextDecoder()
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') {
            callback({ type: 'done' })
          } else {
            try {
              const parsed = JSON.parse(data)
              const text = parsed.content || parsed.text || ''
              callback({ type: 'token', content: text, text })
            } catch {
              callback({ type: 'token', content: data, text: data })
            }
          }
        }
      }
    }
    
    callback({ type: 'done' })
  } catch (error) {
    console.error('Stream error:', error)
    callback({ 
      type: 'error', 
      error: error instanceof Error ? error.message : 'Stream failed' 
    })
  }
}

/**
 * Get available models from the API
 */
export async function getModels(_includeAll?: boolean): Promise<ModelInfo[]> {
  try {
    const response = await fetch(`${API_BASE}/api/models`)
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Models API error:', error)
    // Return default models if API is unavailable
    return [
      { id: 'default', name: 'Default Model', isDefault: true, provider: 'local' },
      { id: 'ft-qwen25-v1-quality', name: 'PersRM Quality', description: 'Fine-tuned model', provider: 'ollama' },
      { id: 'mistral:7b', name: 'Mistral 7B', description: 'Base Mistral model', provider: 'ollama' },
    ]
  }
}

/**
 * Get VSCode/code-server status
 */
export async function getVSCodeStatus(): Promise<VSCodeStatus> {
  try {
    const response = await fetch(`${API_BASE}/api/vscode/status`)
    
    if (!response.ok) {
      // API not available or endpoint doesn't exist - return not running
      return { running: false }
    }
    
    return await response.json()
  } catch {
    // Return not running status if API is unavailable
    return { running: false }
  }
}

/**
 * Check if VSCode/code-server is healthy
 */
export async function checkVSCodeHealth(): Promise<{ healthy: boolean }> {
  try {
    const status = await getVSCodeStatus()
    if (!status.running || !status.url) {
      return { healthy: false }
    }
    
    // Try to reach the code-server
    const response = await fetch(`${status.url}/healthz`, {
      method: 'GET',
      mode: 'no-cors',
    })
    
    return { healthy: true }
  } catch (error) {
    console.error('VSCode health check error:', error)
    return { healthy: false }
  }
}

/**
 * Get list of available projects
 */
export async function getProjects(): Promise<ProjectInfo[]> {
  try {
    const response = await fetch(`${API_BASE}/api/projects`)
    
    if (!response.ok) {
      // API not available - return empty list
      return []
    }
    
    return await response.json()
  } catch {
    // Return empty list if API is unavailable
    return []
  }
}

/**
 * Get file tree for a given path
 */
export async function getFileTree(path?: string): Promise<FileTreeResponse> {
  try {
    const url = path 
      ? `${API_BASE}/api/files?path=${encodeURIComponent(path)}`
      : `${API_BASE}/api/files`
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('File tree API error:', error)
    // Return empty file list if API is unavailable
    return { files: [] }
  }
}

/**
 * Check API health status
 */
export async function checkHealth(): Promise<{ status: string }> {
  try {
    const response = await fetch(`${API_BASE}/api/health`)
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Health check API error:', error)
    return { status: 'unavailable' }
  }
}

/**
 * Start VSCode/code-server with a project
 */
export async function startVSCode(projectPathOrOptions: string | { workspace: string }): Promise<VSCodeStatus> {
  try {
    const path = typeof projectPathOrOptions === 'string' 
      ? projectPathOrOptions 
      : projectPathOrOptions.workspace
      
    const response = await fetch(`${API_BASE}/api/vscode/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Start VSCode API error:', error)
    return { running: false, error: error instanceof Error ? error.message : 'Failed to start VSCode' }
  }
}

/**
 * Stop VSCode/code-server
 */
export async function stopVSCode(): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${API_BASE}/api/vscode/stop`, {
      method: 'POST',
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Stop VSCode API error:', error)
    return { success: false }
  }
}

/**
 * Read file contents
 */
export async function readFile(path: string): Promise<{ content: string }> {
  try {
    const response = await fetch(`${API_BASE}/api/files/read?path=${encodeURIComponent(path)}`)
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    const data = await response.json()
    return { content: data.content || '' }
  } catch (error) {
    console.error('Read file API error:', error)
    return { content: '' }
  }
}

/**
 * Write file contents
 */
export async function writeFile(path: string, content: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${API_BASE}/api/files/write`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, content }),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Write file API error:', error)
    return { success: false }
  }
}

/**
 * Delete a file or directory
 */
export async function deleteFile(path: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${API_BASE}/api/files/delete`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Delete file API error:', error)
    return { success: false }
  }
}

/**
 * Create a directory
 */
export async function createDirectory(path: string): Promise<{ success: boolean }> {
  try {
    const response = await fetch(`${API_BASE}/api/files/mkdir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Create directory API error:', error)
    return { success: false }
  }
}

/**
 * Get file icon based on filename/extension
 */
export function getFileIcon(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  const iconMap: Record<string, string> = {
    // Code files
    'js': '📜',
    'jsx': '⚛️',
    'ts': '📘',
    'tsx': '⚛️',
    'py': '🐍',
    'rb': '💎',
    'go': '🐹',
    'rs': '🦀',
    'java': '☕',
    'c': '🔧',
    'cpp': '🔧',
    'h': '📋',
    'cs': '#️⃣',
    // Web files
    'html': '🌐',
    'css': '🎨',
    'scss': '🎨',
    'less': '🎨',
    'svg': '🖼️',
    // Data files
    'json': '📋',
    'yaml': '📋',
    'yml': '📋',
    'xml': '📋',
    'toml': '📋',
    // Documents
    'md': '📝',
    'txt': '📄',
    'pdf': '📕',
    'doc': '📘',
    'docx': '📘',
    // Config
    'env': '⚙️',
    'gitignore': '🚫',
    'dockerfile': '🐳',
    // Default
    'default': '📄',
  }
  return iconMap[ext] || iconMap['default']
}

/**
 * Import a directory (for project import)
 */
export interface ImportResult {
  success: boolean
  path?: string
  target?: string
  imported_count?: number
  skipped_count?: number
}

export async function importDirectory(sourcePath: string, _targetPath?: string): Promise<ImportResult> {
  try {
    const response = await fetch(`${API_BASE}/api/files/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: sourcePath }),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Import directory API error:', error)
    return { success: false }
  }
}

/**
 * Upload a file
 */
export async function uploadFile(pathOrFile: string | File, file?: File): Promise<{ success: boolean }> {
  try {
    const formData = new FormData()
    
    if (pathOrFile instanceof File) {
      // Called with just File (use file name as path)
      formData.append('file', pathOrFile)
      formData.append('path', pathOrFile.name)
    } else {
      // Called with path and file
      formData.append('file', file!)
      formData.append('path', pathOrFile)
    }
    
    const response = await fetch(`${API_BASE}/api/files/upload`, {
      method: 'POST',
      body: formData,
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Upload file API error:', error)
    return { success: false }
  }
}

/**
 * Execute code in a sandbox
 */
export async function executeCode(
  codeOrOptions: string | { file_path: string; code?: string; language?: string },
  language?: string
): Promise<ExecutionResult> {
  try {
    let body: Record<string, unknown>
    if (typeof codeOrOptions === 'string') {
      body = { code: codeOrOptions, language: language || 'python' }
    } else {
      body = { 
        file_path: codeOrOptions.file_path, 
        code: codeOrOptions.code,
        language: codeOrOptions.language 
      }
    }
    
    const response = await fetch(`${API_BASE}/api/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`)
    }
    
    return await response.json()
  } catch (error) {
    console.error('Execute code API error:', error)
    return {
      success: false,
      output: '',
      error: 'Code execution service is unavailable',
    }
  }
}

/**
 * Get programming language from file path/extension
 */
export function getLanguageFromPath(path: string): string {
  const ext = path.split('.').pop()?.toLowerCase() || ''
  const langMap: Record<string, string> = {
    // JavaScript/TypeScript
    'js': 'javascript',
    'jsx': 'javascript',
    'mjs': 'javascript',
    'cjs': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    // Python
    'py': 'python',
    'pyw': 'python',
    'pyi': 'python',
    // Web
    'html': 'html',
    'htm': 'html',
    'css': 'css',
    'scss': 'scss',
    'sass': 'sass',
    'less': 'less',
    // Data formats
    'json': 'json',
    'yaml': 'yaml',
    'yml': 'yaml',
    'xml': 'xml',
    'toml': 'toml',
    // Markdown
    'md': 'markdown',
    'mdx': 'markdown',
    // Shell
    'sh': 'shell',
    'bash': 'shell',
    'zsh': 'shell',
    'fish': 'shell',
    // Other languages
    'go': 'go',
    'rs': 'rust',
    'rb': 'ruby',
    'php': 'php',
    'java': 'java',
    'kt': 'kotlin',
    'swift': 'swift',
    'c': 'c',
    'cpp': 'cpp',
    'cc': 'cpp',
    'cxx': 'cpp',
    'h': 'c',
    'hpp': 'cpp',
    'cs': 'csharp',
    'sql': 'sql',
    'r': 'r',
    'lua': 'lua',
    'pl': 'perl',
    'ex': 'elixir',
    'exs': 'elixir',
    'erl': 'erlang',
    'hs': 'haskell',
    'clj': 'clojure',
    'scala': 'scala',
    'vue': 'vue',
    'svelte': 'svelte',
    // Config files
    'dockerfile': 'dockerfile',
    'makefile': 'makefile',
    'env': 'dotenv',
    'gitignore': 'gitignore',
  }
  return langMap[ext] || 'plaintext'
}

