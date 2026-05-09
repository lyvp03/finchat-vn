import { ApiError } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://finchat-api-45o9.onrender.com";

export interface FetchOptions extends RequestInit {
  timeout?: number;
}

export async function fetchAPI<T>(path: string, options?: FetchOptions): Promise<T> {
  const { timeout = 30000, ...fetchOptions } = options || {};

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers: { "Content-Type": "application/json", ...fetchOptions.headers },
      signal: fetchOptions.signal || controller.signal,
    });

    clearTimeout(id);

    if (!res.ok) {
      let errorMessage = "Đã xảy ra lỗi không xác định.";
      if (res.status === 429) errorMessage = "Quá nhiều yêu cầu, vui lòng thử lại sau.";
      else if (res.status >= 500) errorMessage = "Máy chủ đang lỗi, vui lòng thử lại sau.";
      
      const error: ApiError = {
        status: res.status,
        message: errorMessage,
      };
      throw error;
    }

    return await res.json();
  } catch (err: any) {
    clearTimeout(id);
    
    if (err.name === "AbortError") {
      throw { status: 408, message: "Yêu cầu hết hạn hoặc đã bị hủy." } as ApiError;
    }
    
    if (err.status) throw err; // Already normalized

    throw { 
      status: 0, 
      message: "Không thể kết nối máy chủ, vui lòng thử lại." 
    } as ApiError;
  }
}

/**
 * Fetch with cache support — returns cached data immediately and revalidates in background.
 * Uses stale-while-revalidate pattern for near-instant perceived loads.
 */
export async function fetchWithSWR<T>(
  path: string,
  options?: FetchOptions & { ttlMs?: number }
): Promise<{ data: T; fromCache: boolean }> {
  const { ttlMs = 60000, ...fetchOpts } = options || {};
  const cacheKey = `swr:${path}`;

  // Try sessionStorage for cross-navigation persistence
  try {
    const raw = sessionStorage.getItem(cacheKey);
    if (raw) {
      const entry = JSON.parse(raw);
      if (Date.now() < entry.expiry) {
        // Return cached data immediately, revalidate in background
        fetchAPI<T>(path, fetchOpts)
          .then((freshData) => {
            sessionStorage.setItem(cacheKey, JSON.stringify({
              data: freshData,
              expiry: Date.now() + ttlMs,
            }));
          })
          .catch(() => {}); // Silently ignore bg revalidation errors
        return { data: entry.data as T, fromCache: true };
      }
    }
  } catch {
    // sessionStorage unavailable (SSR), continue with fetch
  }

  const data = await fetchAPI<T>(path, fetchOpts);

  try {
    sessionStorage.setItem(cacheKey, JSON.stringify({
      data,
      expiry: Date.now() + ttlMs,
    }));
  } catch {
    // Storage full or unavailable
  }

  return { data, fromCache: false };
}
