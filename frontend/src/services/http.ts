import type { ActiveGame, BackendService, GameMode, ScoreEntry, User } from "./types";

// Base URL for the backend API (mounted under /api per openapi.yaml).
// - Override with VITE_API_BASE_URL for any environment.
// - In dev, default to the standalone uvicorn server on :8000.
// - In prod, default to a same-origin /api mount.
const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  (import.meta.env.DEV ? "http://localhost:8000/api" : "/api");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      if (body?.error) message = body.error;
    } catch {
      // non-JSON error body; fall back to statusText
    }
    const error = new Error(message) as Error & { status: number };
    error.status = res.status;
    throw error;
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// Treat a 401 as a no-op for best-effort, fire-and-forget mutations of the
// caller's own data (publish/clear live game), matching the mock's behavior
// when logged out. Other errors still reject.
function ignore401(p: Promise<void>): Promise<void> {
  return p.catch((err: Error & { status?: number }) => {
    if (err?.status === 401) return;
    throw err;
  });
}

// Subscribe to a Server-Sent Events stream. Each event's `data` is JSON; the
// server emits an initial snapshot on connect. Returns an unsubscribe function.
function subscribe<T>(path: string, cb: (value: T) => void): () => void {
  if (typeof EventSource === "undefined") return () => {};

  const es = new EventSource(`${API_BASE}${path}`, { withCredentials: true });
  es.onmessage = (e) => {
    try {
      cb(JSON.parse(e.data) as T);
    } catch {
      // ignore malformed frames
    }
  };
  return () => es.close();
}

export function createHttpService(): BackendService {
  return {
    signup(username, password) {
      return request<User>("/auth/signup", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
    },

    login(username, password) {
      return request<User>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      });
    },

    logout() {
      return request<void>("/auth/logout", { method: "POST" });
    },

    currentUser() {
      return request<User | null>("/auth/me");
    },

    submitScore(mode, score) {
      return request<ScoreEntry>("/scores", {
        method: "POST",
        body: JSON.stringify({ mode, score }),
      });
    },

    getLeaderboard(mode, limit = 10) {
      const params = new URLSearchParams({ mode, limit: String(limit) });
      return request<ScoreEntry[]>(`/scores?${params}`);
    },

    publishGameState(state, mode, score) {
      // Best-effort publish of the caller's own live game; a no-op when logged
      // out (matches the mock), so a 401 is swallowed rather than rejected.
      return ignore401(
        request<void>("/active-games/me", {
          method: "PUT",
          body: JSON.stringify({ state, mode, score }),
        }),
      );
    },

    endGame() {
      // Fire-and-forget on game over / unmount; no-op when logged out.
      return ignore401(request<void>("/active-games/me", { method: "DELETE" }));
    },

    listActiveGames() {
      return request<ActiveGame[]>("/active-games");
    },

    getActiveGame(userId) {
      return request<ActiveGame | null>(`/active-games/${encodeURIComponent(userId)}`);
    },

    subscribeToActiveGames(cb) {
      return subscribe<ActiveGame[]>("/active-games/stream", cb);
    },

    subscribeToActiveGame(userId, cb) {
      return subscribe<ActiveGame | null>(`/active-games/${encodeURIComponent(userId)}/stream`, cb);
    },
  };
}
