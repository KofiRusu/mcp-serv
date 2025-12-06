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
}

export interface ModelInfo {
  id: string
  name: string
  description?: string
  isDefault?: boolean
  provider?: string
  model_id?: string
  enabled?: boolean
  is_council_member?: boolean
}

export interface StreamEvent {
  type: 'token' | 'done' | 'error'
  content?: string
  error?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Send a chat message to the API
 */
export async function sendChatMessage(
  message: string,
  model?: string,
  conversationId?: string
): Promise<ChatResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        model: model || 'default',
        conversation_id: conversationId,
      }),
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

/**
 * Stream a chat message from the API
 */
export async function* streamChatMessage(
  message: string,
  model?: string,
  conversationId?: string
): AsyncGenerator<StreamEvent> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        model: model || 'default',
        conversation_id: conversationId,
      }),
    })
    
    if (!response.ok) {
      yield { type: 'error', error: `API error: ${response.status}` }
      return
    }
    
    const reader = response.body?.getReader()
    if (!reader) {
      yield { type: 'error', error: 'No response body' }
      return
    }
    
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
            yield { type: 'done' }
          } else {
            try {
              const parsed = JSON.parse(data)
              yield { type: 'token', content: parsed.content || parsed.text || '' }
            } catch {
              yield { type: 'token', content: data }
            }
          }
        }
      }
    }
    
    yield { type: 'done' }
  } catch (error) {
    console.error('Stream error:', error)
    yield { 
      type: 'error', 
      error: error instanceof Error ? error.message : 'Stream failed' 
    }
  }
}

/**
 * Get available models from the API
 */
// Default Ollama models to show when backend is unavailable
const DEFAULT_MODELS: ModelInfo[] = [
  {
    id: "ollama-llama3.2",
    name: "Llama 3.2",
    provider: "ollama",
    model_id: "llama3.2:latest",
    enabled: true,
    is_council_member: false,
    isDefault: true,
  },
  {
    id: "ollama-qwen2.5",
    name: "Qwen 2.5",
    provider: "ollama",
    model_id: "qwen2.5:latest",
    enabled: true,
    is_council_member: false,
  },
  {
    id: "ollama-mistral",
    name: "Mistral",
    provider: "ollama",
    model_id: "mistral:latest",
    enabled: true,
    is_council_member: false,
  },
  {
    id: "ollama-codellama",
    name: "CodeLlama",
    provider: "ollama",
    model_id: "codellama:latest",
    enabled: true,
    is_council_member: false,
  },
  {
    id: "ollama-deepseek-coder",
    name: "DeepSeek Coder",
    provider: "ollama",
    model_id: "deepseek-coder:latest",
    enabled: true,
    is_council_member: false,
  },
  {
    id: 'ft-qwen25-v1-quality',
    name: 'PersRM Quality',
    description: 'Fine-tuned PersRM model',
    provider: 'local',
    enabled: true,
    is_council_member: false,
  },
]

export async function getModels(enabledOnly: boolean = false): Promise<ModelInfo[]> {
  try {
    const url = new URL(`${API_BASE}/api/models`)
    if (enabledOnly) {
      url.searchParams.set("enabled_only", "true")
    }
    
    const response = await fetch(url.toString())
    
    if (!response.ok) {
      console.warn(`Models API unavailable: ${response.statusText}`)
      return DEFAULT_MODELS
    }
    
    const models = await response.json()
    // If API returns empty, still show defaults
    return models.length > 0 ? models : DEFAULT_MODELS
  } catch (error) {
    console.error('Models API error:', error)
    // Return default Ollama models if API is unavailable
    return DEFAULT_MODELS
  }
}

/**
 * Check API health
 */
export async function checkHealth(): Promise<{
  status: string
  version: string
  models_loaded: number
  rag_documents: number
}> {
  const response = await fetch(`${API_BASE}/api/health`)
  if (!response.ok) {
    throw new Error("API is not healthy")
  }
  return response.json()
}

export interface FileInfo {
  name: string
  path: string
  is_directory: boolean
  size?: number
  modified?: string
  children?: FileInfo[]
}

export interface ExecutionResult {
  stdout: string
  stderr: string
  exit_code: number
  execution_time: number
}

// File icons mapping
const FILE_ICONS: Record<string, string> = {
  '.ts': '📘',
  '.tsx': '⚛️',
  '.js': '📒',
  '.jsx': '⚛️',
  '.json': '📋',
  '.py': '🐍',
  '.css': '🎨',
  '.html': '🌐',
  '.md': '📝',
  '.sh': '🖥️',
  '.yml': '⚙️',
  '.yaml': '⚙️',
  'package.json': '📦',
  'tsconfig.json': '⚙️',
  'Dockerfile': '🐳',
  '.gitignore': '🙈',
  'default': '📄',
}

/**
 * Get icon for a file based on extension
 */
export function getFileIcon(filename: string): string {
  if (FILE_ICONS[filename]) {
    return FILE_ICONS[filename]
  }
  const ext = filename.includes(".") ? `.${filename.split(".").pop()}` : ""
  return FILE_ICONS[ext] || FILE_ICONS.default
}

// Language mapping for Monaco editor
const LANGUAGE_MAP: Record<string, string> = {
  '.ts': 'typescript',
  '.tsx': 'typescript',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.json': 'json',
  '.py': 'python',
  '.css': 'css',
  '.scss': 'scss',
  '.html': 'html',
  '.md': 'markdown',
  '.sh': 'shell',
  '.bash': 'shell',
  '.yml': 'yaml',
  '.yaml': 'yaml',
  '.sql': 'sql',
  '.go': 'go',
  '.rs': 'rust',
  '.java': 'java',
  '.c': 'c',
  '.cpp': 'cpp',
  '.h': 'c',
  '.hpp': 'cpp',
}

/**
 * Get language identifier for Monaco editor
 */
export function getLanguageFromPath(filepath: string): string {
  const ext = filepath.includes(".") ? `.${filepath.split(".").pop()}` : ""
  return LANGUAGE_MAP[ext] || 'plaintext'
}

/**
 * Get file tree for the sandbox
 */
export async function getFileTree(path?: string): Promise<FileInfo[]> {
  const url = new URL(`${API_BASE}/api/sandbox/files`)
  if (path) {
    url.searchParams.set("path", path)
  }
  
  try {
    const response = await fetch(url.toString())
    if (!response.ok) {
      console.warn(`File tree API unavailable: ${response.statusText}`)
      return []
    }
    return response.json()
  } catch (error) {
    console.warn("File tree API unavailable:", error)
    return []
  }
}

/**
 * Delete a file or directory
 */
export async function deleteFile(filepath: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sandbox/file`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: filepath }),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to delete file: ${response.statusText}`)
  }
}

/**
 * Create a directory
 */
export async function createDirectory(dirpath: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sandbox/directory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: dirpath }),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to create directory: ${response.statusText}`)
  }
}

/**
 * Upload a file to the sandbox
 */
export async function uploadFile(file: File, targetPath: string): Promise<FileInfo> {
  const formData = new FormData()
  formData.append("file", file)
  formData.append("path", targetPath)
  
  const response = await fetch(`${API_BASE}/api/sandbox/upload`, {
    method: "POST",
    body: formData,
  })
  
  if (!response.ok) {
    throw new Error(`Failed to upload file: ${response.statusText}`)
  }
  
  return response.json()
}

/**
 * Import a directory from the local filesystem
 */
export async function importDirectory(sourcePath: string): Promise<FileInfo[]> {
  const response = await fetch(`${API_BASE}/api/sandbox/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_path: sourcePath }),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to import directory: ${response.statusText}`)
  }
  
  return response.json()
}

/**
 * Read a file's contents
 */
export async function readFile(filepath: string): Promise<string> {
  const url = new URL(`${API_BASE}/api/sandbox/file`)
  url.searchParams.set("path", filepath)
  
  try {
    const response = await fetch(url.toString())
    if (!response.ok) {
      console.warn(`Failed to read file: ${response.statusText}`)
      return ""
    }
    const data = await response.json()
    return data.content
  } catch (error) {
    console.warn("File read error:", error)
    return ""
  }
}

/**
 * Write content to a file
 */
export async function writeFile(filepath: string, content: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/sandbox/file`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: filepath, content }),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to write file: ${response.statusText}`)
  }
}

/**
 * Execute code in the sandbox
 */
export async function executeCode(options: {
  file_path: string
  timeout?: number
  args?: string[]
}): Promise<ExecutionResult> {
  try {
    const response = await fetch(`${API_BASE}/api/sandbox/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        path: options.file_path,
        timeout: options.timeout,
        args: options.args,
      }),
    })

    if (!response.ok) {
      return {
        stdout: "",
        stderr: `API Error: ${response.statusText}`,
        exit_code: 1,
        execution_time: 0,
      }
    }
    return response.json()
  } catch (error) {
    return {
      stdout: "",
      stderr: `Network Error: ${error instanceof Error ? error.message : "Unknown error"}`,
      exit_code: 1,
      execution_time: 0,
    }
  }
}

// =============================================================================
// VSCode/Code-Server Integration
// =============================================================================

export interface VSCodeStatus {
  running: boolean
  url?: string
  port?: number
  workspace?: string
  error?: string
}

/**
 * Get VSCode/code-server status
 */
export async function getVSCodeStatus(): Promise<VSCodeStatus> {
  try {
    const response = await fetch(`${API_BASE}/api/vscode/status`)
    if (!response.ok) {
      return { running: false, error: response.statusText }
    }
    return response.json()
  } catch (error) {
    // Backend unavailable
    console.warn("VSCode API unavailable:", error)
    return { running: false, error: "Backend unavailable" }
  }
}

/**
 * Check if VSCode/code-server is healthy and responding
 */
export async function checkVSCodeHealth(): Promise<{ healthy: boolean; latency?: number }> {
  const start = Date.now()
  try {
    const status = await getVSCodeStatus()
    if (!status.running || !status.url) {
      return { healthy: false }
    }
    
    // Try to ping the code-server
    const response = await fetch(`${status.url}/healthz`, {
      method: "GET",
      mode: "no-cors",
    }).catch(() => null)
    
    return {
      healthy: response !== null,
      latency: Date.now() - start,
    }
  } catch {
    return { healthy: false }
  }
}

/**
 * Start VSCode/code-server
 */
export async function startVSCode(workspace?: string): Promise<VSCodeStatus> {
  try {
    const response = await fetch(`${API_BASE}/api/vscode/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ workspace }),
    })
    
    if (!response.ok) {
      return { running: false, error: `Failed to start: ${response.statusText}` }
    }
    
    return response.json()
  } catch (error) {
    return { running: false, error: `Network error: ${error instanceof Error ? error.message : "Unknown"}` }
  }
}

/**
 * Stop VSCode/code-server
 */
export async function stopVSCode(): Promise<void> {
  try {
    await fetch(`${API_BASE}/api/vscode/stop`, {
      method: "POST",
    })
  } catch (error) {
    console.warn("Failed to stop VSCode:", error)
  }
}

// =============================================================================
// Projects Management
// =============================================================================

export interface ProjectInfo {
  id: string
  name: string
  path: string
  description?: string
  language?: string
  created_at: string
  last_opened?: string
  is_git?: boolean
  exists?: boolean
}

// Default projects to show when backend is unavailable
const DEFAULT_PROJECTS: ProjectInfo[] = [
  {
    id: "chatos",
    name: "ChatOS",
    path: "~/ChatOS-v2.0",
    description: "ChatOS AI Assistant",
    language: "Python",
    created_at: new Date().toISOString(),
    exists: true,
  },
  {
    id: "sandbox-ui",
    name: "Sandbox UI",
    path: "~/ChatOS-v2.0/sandbox-ui",
    description: "Next.js Frontend",
    language: "TypeScript",
    created_at: new Date().toISOString(),
    exists: true,
  },
  {
    id: "home",
    name: "Home Directory",
    path: "~",
    description: "User home directory",
    created_at: new Date().toISOString(),
    exists: true,
  },
]

/**
 * Get list of projects
 */
export async function getProjects(): Promise<ProjectInfo[]> {
  try {
    const response = await fetch(`${API_BASE}/api/projects`)
    if (!response.ok) {
      console.warn(`Projects API unavailable: ${response.statusText}`)
      return DEFAULT_PROJECTS
    }
    const projects = await response.json()
    // If API returns empty, still show defaults
    return projects.length > 0 ? projects : DEFAULT_PROJECTS
  } catch (error) {
    // Backend unavailable - return default projects
    console.warn("Projects API unavailable:", error)
    return DEFAULT_PROJECTS
  }
}

/**
 * Create a new project
 */
export async function createProject(project: {
  name: string
  path?: string
  description?: string
  language?: string
}): Promise<ProjectInfo> {
  const response = await fetch(`${API_BASE}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(project),
  })
  
  if (!response.ok) {
    throw new Error(`Failed to create project: ${response.statusText}`)
  }
  
  return response.json()
}

/**
 * Delete a project
 */
export async function deleteProject(projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/projects/${projectId}`, {
    method: "DELETE",
  })
  
  if (!response.ok) {
    throw new Error(`Failed to delete project: ${response.statusText}`)
  }
}

/**
 * Open a project in VSCode
 */
export async function openProjectInVSCode(projectId: string): Promise<VSCodeStatus> {
  try {
    const response = await fetch(`${API_BASE}/api/projects/${projectId}/open`, {
      method: "POST",
    })
    
    if (!response.ok) {
      return { running: false, error: `Failed to open project: ${response.statusText}` }
    }
    
    return response.json()
  } catch (error) {
    return { running: false, error: `Network error: ${error instanceof Error ? error.message : "Unknown"}` }
  }
}

