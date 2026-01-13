/**
 * ChatOS API Hooks with SWR
 * 
 * Provides optimized data fetching with:
 * - SWR for automatic caching and revalidation
 * - Debouncing for search and input operations
 * - Optimistic updates for better UX
 */

import useSWR, { SWRConfiguration, mutate } from 'swr';
import { useCallback, useRef, useEffect, useState } from 'react';
import {
  getFileTree,
  getModels,
  checkHealth,
  getProjects,
  getVSCodeStatus,
  FileTreeResponse,
  ModelInfo,
  ProjectInfo,
  VSCodeStatus,
} from '@/lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''; // Empty = same origin

// =============================================================================
// SWR Configuration
// =============================================================================

/**
 * Default fetcher for SWR
 */
const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error('API request failed');
    throw error;
  }
  return res.json();
};

/**
 * Default SWR options for different data types
 */
const swrConfigs = {
  // Fast-changing data (revalidate frequently)
  realtime: {
    refreshInterval: 5000,
    revalidateOnFocus: true,
    dedupingInterval: 2000,
  } as SWRConfiguration,
  
  // Semi-static data (revalidate occasionally)
  standard: {
    refreshInterval: 30000,
    revalidateOnFocus: true,
    dedupingInterval: 5000,
  } as SWRConfiguration,
  
  // Static data (rarely changes)
  static: {
    refreshInterval: 0,
    revalidateOnFocus: false,
    dedupingInterval: 60000,
  } as SWRConfiguration,
};

// =============================================================================
// Debounce Hook
// =============================================================================

/**
 * Debounce a value with configurable delay
 */
export function useDebounce<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Debounced callback function
 */
export function useDebouncedCallback<T extends (...args: unknown[]) => unknown>(
  callback: T,
  delay: number = 300
): T {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const callbackRef = useRef(callback);

  // Keep callback ref updated
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }

      timeoutRef.current = setTimeout(() => {
        callbackRef.current(...args);
      }, delay);
    },
    [delay]
  ) as T;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  return debouncedCallback;
}

// =============================================================================
// API Hooks
// =============================================================================

/**
 * Hook for file tree with automatic refresh
 */
export function useFileTree(options?: SWRConfiguration) {
  return useSWR<FileTreeResponse>(
    `${API_BASE}/api/sandbox/files`,
    () => getFileTree(),
    {
      ...swrConfigs.standard,
      ...options,
    }
  );
}

/**
 * Hook for models list
 */
export function useModels(enabledOnly = true, options?: SWRConfiguration) {
  return useSWR<ModelInfo[]>(
    `${API_BASE}/api/models?enabled_only=${enabledOnly}`,
    () => getModels(enabledOnly),
    {
      ...swrConfigs.static,
      ...options,
    }
  );
}

/**
 * Hook for health check
 */
export function useHealth(options?: SWRConfiguration) {
  return useSWR(
    `${API_BASE}/api/health`,
    () => checkHealth(),
    {
      ...swrConfigs.realtime,
      ...options,
    }
  );
}

/**
 * Hook for projects list
 */
export function useProjects(options?: SWRConfiguration) {
  return useSWR<ProjectInfo[]>(
    `${API_BASE}/api/sandbox/projects`,
    () => getProjects(),
    {
      ...swrConfigs.standard,
      ...options,
    }
  );
}

/**
 * Hook for VSCode status
 */
export function useVSCodeStatus(options?: SWRConfiguration) {
  return useSWR<VSCodeStatus>(
    `${API_BASE}/api/sandbox/vscode/status`,
    () => getVSCodeStatus(),
    {
      ...swrConfigs.realtime,
      ...options,
    }
  );
}

/**
 * Hook for cache statistics
 */
export function useCacheStats(options?: SWRConfiguration) {
  return useSWR(
    `${API_BASE}/api/cache/stats`,
    fetcher,
    {
      ...swrConfigs.realtime,
      ...options,
    }
  );
}

// =============================================================================
// Mutation Helpers
// =============================================================================

/**
 * Invalidate file tree cache (call after file operations)
 */
export function invalidateFileTree() {
  return mutate(`${API_BASE}/api/sandbox/files`);
}

/**
 * Invalidate models cache
 */
export function invalidateModels() {
  return mutate((key) => typeof key === 'string' && key.includes('/api/models'));
}

/**
 * Invalidate projects cache
 */
export function invalidateProjects() {
  return mutate(`${API_BASE}/api/sandbox/projects`);
}

/**
 * Invalidate all caches
 */
export function invalidateAll() {
  return mutate(() => true);
}

// =============================================================================
// Optimistic Update Helpers
// =============================================================================

/**
 * Perform optimistic update on file tree
 */
export async function optimisticFileTreeUpdate<T>(
  updateFn: (current: FileTreeResponse | undefined) => FileTreeResponse | undefined,
  asyncFn: () => Promise<T>
): Promise<T> {
  const key = `${API_BASE}/api/sandbox/files`;
  
  // Optimistically update
  await mutate(key, updateFn, false);
  
  try {
    // Perform actual operation
    const result = await asyncFn();
    
    // Revalidate
    await mutate(key);
    
    return result;
  } catch (error) {
    // Revalidate on error to restore correct state
    await mutate(key);
    throw error;
  }
}

// =============================================================================
// Prefetch Helpers
// =============================================================================

/**
 * Prefetch file tree
 */
export function prefetchFileTree() {
  return mutate(`${API_BASE}/api/sandbox/files`, getFileTree());
}

/**
 * Prefetch models
 */
export function prefetchModels() {
  return mutate(`${API_BASE}/api/models?enabled_only=true`, getModels(true));
}

/**
 * Prefetch all common data on app start
 */
export async function prefetchCommonData() {
  await Promise.all([
    prefetchFileTree(),
    prefetchModels(),
  ]);
}

