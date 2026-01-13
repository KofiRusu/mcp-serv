/**
 * Authentication utilities for Keycloak OAuth integration
 */

// Keycloak configuration
export const KEYCLOAK_CONFIG = {
    url: typeof window !== 'undefined' ? `${window.location.origin}/auth` : 'http://localhost:8080/auth',
    realm: 'chatos',
    clientId: 'chatos-app',
  }
  
  // Build Keycloak authorization URL
  export function getKeycloakAuthUrl(redirectUri?: string): string {
    const params = new URLSearchParams({
      client_id: KEYCLOAK_CONFIG.clientId,
      redirect_uri: redirectUri || getCallbackUrl(),
      response_type: 'code',
      scope: 'openid profile email',
    })
  
    return `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/auth?${params.toString()}`
  }
  
  // Build Keycloak registration URL
  export function getKeycloakRegisterUrl(redirectUri?: string): string {
    const params = new URLSearchParams({
      client_id: KEYCLOAK_CONFIG.clientId,
      redirect_uri: redirectUri || getCallbackUrl(),
      response_type: 'code',
      scope: 'openid profile email',
    })
  
    return `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/registrations?${params.toString()}`
  }
  
  // Get callback URL
  export function getCallbackUrl(): string {
    if (typeof window !== 'undefined') {
      return `${window.location.origin}/auth/callback`
    }
    return 'http://localhost:3000/auth/callback'
  }
  
  // Build Keycloak logout URL
  export function getKeycloakLogoutUrl(redirectUri?: string): string {
    const params = new URLSearchParams({
      client_id: KEYCLOAK_CONFIG.clientId,
      post_logout_redirect_uri: redirectUri || (typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000'),
    })
  
    return `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/logout?${params.toString()}`
  }
  
  // Token storage keys
  const ACCESS_TOKEN_KEY = 'chatos_access_token'
  const REFRESH_TOKEN_KEY = 'chatos_refresh_token'
  const TOKEN_EXPIRY_KEY = 'chatos_token_expiry'
  const USER_INFO_KEY = 'chatos_user_info'
  const REDIRECT_URI_KEY = 'chatos_redirect_uri'
  
  // Token storage functions
  export function storeTokens(accessToken: string, refreshToken?: string, expiresIn?: number): void {
    if (typeof window === 'undefined') return
  
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
    
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
    }
    
    if (expiresIn) {
      const expiryTime = Date.now() + expiresIn * 1000
      localStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString())
    }
  }
  
  export function getAccessToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(ACCESS_TOKEN_KEY)
  }
  
  export function getRefreshToken(): string | null {
    if (typeof window === 'undefined') return null
    return localStorage.getItem(REFRESH_TOKEN_KEY)
  }
  
  export function isTokenExpired(): boolean {
    if (typeof window === 'undefined') return true
    
    const expiry = localStorage.getItem(TOKEN_EXPIRY_KEY)
    if (!expiry) return true
    
    // Consider token expired 30 seconds before actual expiry
    return Date.now() > parseInt(expiry) - 30000
  }
  
  export function clearTokens(): void {
    if (typeof window === 'undefined') return
    
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(TOKEN_EXPIRY_KEY)
    localStorage.removeItem(USER_INFO_KEY)
  }
  
  // User info storage
  export interface UserInfo {
    id: string
    username: string
    email: string
    name: string
    roles: string[]
    isAdmin: boolean
  }
  
  export function storeUserInfo(userInfo: UserInfo): void {
    if (typeof window === 'undefined') return
    localStorage.setItem(USER_INFO_KEY, JSON.stringify(userInfo))
  }
  
  export function getUserInfo(): UserInfo | null {
    if (typeof window === 'undefined') return null
    
    const stored = localStorage.getItem(USER_INFO_KEY)
    if (!stored) return null
    
    try {
      return JSON.parse(stored)
    } catch {
      return null
    }
  }
  
  // Redirect URI storage (for post-login redirect)
  export function storeRedirectUri(uri: string): void {
    if (typeof window === 'undefined') return
    sessionStorage.setItem(REDIRECT_URI_KEY, uri)
  }
  
  export function getAndClearRedirectUri(): string | null {
    if (typeof window === 'undefined') return null
    
    const uri = sessionStorage.getItem(REDIRECT_URI_KEY)
    sessionStorage.removeItem(REDIRECT_URI_KEY)
    return uri
  }
  
  // Check if user is authenticated
  export function isAuthenticated(): boolean {
    const token = getAccessToken()
    if (!token) return false
    
    // Check if token is expired
    if (isTokenExpired()) {
      // Could implement token refresh here
      return false
    }
    
    return true
  }
  
  // Parse JWT token payload (without verification)
  export function parseJwtPayload(token: string): Record<string, unknown> | null {
    try {
      const parts = token.split('.')
      if (parts.length !== 3) return null
      
      const payload = parts[1]
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
      return JSON.parse(decoded)
    } catch {
      return null
    }
  }
  
  // Extract user info from JWT token
  export function extractUserFromToken(token: string): UserInfo | null {
    const payload = parseJwtPayload(token)
    if (!payload) return null
    
    const realmAccess = payload.realm_access as { roles?: string[] } | undefined
    const roles = realmAccess?.roles || []
    
    return {
      id: payload.sub as string || '',
      username: payload.preferred_username as string || '',
      email: payload.email as string || '',
      name: payload.name as string || payload.preferred_username as string || '',
      roles,
      isAdmin: roles.includes('admin') || roles.includes('realm-admin') || roles.includes('chatos-admin'),
    }
  }
  
  // Exchange authorization code for tokens
  export async function exchangeCodeForTokens(code: string): Promise<{
    access_token: string
    refresh_token?: string
    expires_in?: number
    token_type: string
  }> {
    const tokenUrl = `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/token`
    
    const params = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: KEYCLOAK_CONFIG.clientId,
      code,
      redirect_uri: getCallbackUrl(),
    })
    
    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: params.toString(),
    })
    
    if (!response.ok) {
      const error = await response.text()
      throw new Error(`Token exchange failed: ${error}`)
    }
    
    return response.json()
  }
  
  // Refresh access token
  export async function refreshAccessToken(): Promise<string | null> {
    const refreshToken = getRefreshToken()
    if (!refreshToken) return null
    
    const tokenUrl = `${KEYCLOAK_CONFIG.url}/realms/${KEYCLOAK_CONFIG.realm}/protocol/openid-connect/token`
    
    const params = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: KEYCLOAK_CONFIG.clientId,
      refresh_token: refreshToken,
    })
    
    try {
      const response = await fetch(tokenUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: params.toString(),
      })
      
      if (!response.ok) {
        clearTokens()
        return null
      }
      
      const data = await response.json()
      storeTokens(data.access_token, data.refresh_token, data.expires_in)
      
      return data.access_token
    } catch {
      clearTokens()
      return null
    }
  }
  
  // Check if request is from localhost
  export function isLocalhost(): boolean {
    if (typeof window === 'undefined') return false
    
    const hostname = window.location.hostname
    return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'
  }