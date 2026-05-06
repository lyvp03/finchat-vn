/**
 * Simple in-memory cache for API read requests.
 * Used to reduce redundant fetches for dashboard/prices/news data.
 */

interface CacheEntry<T> {
  data: T;
  expiry: number;
}

const cacheStore = new Map<string, CacheEntry<any>>();

export function getCached<T>(key: string): T | null {
  const entry = cacheStore.get(key);
  if (!entry) return null;
  
  if (Date.now() > entry.expiry) {
    cacheStore.delete(key);
    return null;
  }
  
  return entry.data as T;
}

export function setCached<T>(key: string, data: T, ttlMs: number): void {
  cacheStore.set(key, {
    data,
    expiry: Date.now() + ttlMs,
  });
}

export function clearCachePrefix(prefix: string): void {
  for (const key of cacheStore.keys()) {
    if (key.startsWith(prefix)) {
      cacheStore.delete(key);
    }
  }
}

export function clearAllCache(): void {
  cacheStore.clear();
}
