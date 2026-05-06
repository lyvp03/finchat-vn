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
