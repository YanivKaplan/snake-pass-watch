import type { ActiveGame, BackendService, GameMode, ScoreEntry, User } from "./types";

const LS_USERS = "snake.users";
const LS_SESSION = "snake.session";
const LS_SCORES = "snake.scores";
const LS_ACTIVE = "snake.active";

type StoredUser = User & { password: string };

const isBrowser = typeof window !== "undefined";

function read<T>(key: string, fallback: T): T {
  if (!isBrowser) return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write<T>(key: string, value: T): void {
  if (!isBrowser) return;
  window.localStorage.setItem(key, JSON.stringify(value));
  // notify same-tab subscribers
  window.dispatchEvent(new CustomEvent("snake-storage", { detail: { key } }));
}

function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

type Listener<T> = (v: T) => void;
const activeListeners = new Set<Listener<ActiveGame[]>>();

function notifyActive() {
  const games = read<ActiveGame[]>(LS_ACTIVE, []);
  activeListeners.forEach((cb) => cb(games));
}

if (isBrowser) {
  window.addEventListener("snake-storage", (e: Event) => {
    const detail = (e as CustomEvent).detail as { key: string };
    if (detail?.key === LS_ACTIVE) notifyActive();
  });
  window.addEventListener("storage", (e) => {
    if (e.key === LS_ACTIVE) notifyActive();
  });
}

export function createMockService(): BackendService {
  async function currentUser(): Promise<User | null> {
    return read<User | null>(LS_SESSION, null);
  }

  return {
    async signup(username, password) {
      const users = read<StoredUser[]>(LS_USERS, []);
      if (users.some((u) => u.username.toLowerCase() === username.toLowerCase())) {
        throw new Error("Username already taken");
      }
      if (username.trim().length < 2) throw new Error("Username too short");
      if (password.length < 4) throw new Error("Password too short");
      const user: StoredUser = { id: uid(), username, password };
      users.push(user);
      write(LS_USERS, users);
      const session: User = { id: user.id, username: user.username };
      write(LS_SESSION, session);
      return session;
    },

    async login(username, password) {
      const users = read<StoredUser[]>(LS_USERS, []);
      const found = users.find(
        (u) => u.username.toLowerCase() === username.toLowerCase() && u.password === password,
      );
      if (!found) throw new Error("Invalid credentials");
      const session: User = { id: found.id, username: found.username };
      write(LS_SESSION, session);
      return session;
    },

    async logout() {
      if (isBrowser) window.localStorage.removeItem(LS_SESSION);
    },

    currentUser,

    async submitScore(mode, score) {
      const user = await currentUser();
      if (!user) throw new Error("Not authenticated");
      const entry: ScoreEntry = {
        id: uid(),
        userId: user.id,
        username: user.username,
        mode,
        score,
        createdAt: Date.now(),
      };
      const scores = read<ScoreEntry[]>(LS_SCORES, []);
      scores.push(entry);
      write(LS_SCORES, scores);
      return entry;
    },

    async getLeaderboard(mode, limit = 10) {
      const scores = read<ScoreEntry[]>(LS_SCORES, []);
      // best score per user
      const bestByUser = new Map<string, ScoreEntry>();
      for (const s of scores) {
        if (s.mode !== mode) continue;
        const cur = bestByUser.get(s.userId);
        if (!cur || s.score > cur.score) bestByUser.set(s.userId, s);
      }
      return [...bestByUser.values()].sort((a, b) => b.score - a.score).slice(0, limit);
    },

    async publishGameState(state, mode, score) {
      const user = await currentUser();
      if (!user) return;
      const games = read<ActiveGame[]>(LS_ACTIVE, []);
      const filtered = games.filter((g) => g.userId !== user.id);
      filtered.push({
        userId: user.id,
        username: user.username,
        mode,
        score,
        state,
        updatedAt: Date.now(),
      });
      write(LS_ACTIVE, filtered);
    },

    async endGame() {
      const user = await currentUser();
      if (!user) return;
      const games = read<ActiveGame[]>(LS_ACTIVE, []);
      write(
        LS_ACTIVE,
        games.filter((g) => g.userId !== user.id),
      );
    },

    async listActiveGames() {
      const games = read<ActiveGame[]>(LS_ACTIVE, []);
      // prune stale (>30s)
      const fresh = games.filter((g) => Date.now() - g.updatedAt < 30_000);
      return fresh.sort((a, b) => b.score - a.score);
    },

    async getActiveGame(userId) {
      const games = read<ActiveGame[]>(LS_ACTIVE, []);
      return games.find((g) => g.userId === userId) ?? null;
    },

    subscribeToActiveGames(cb) {
      activeListeners.add(cb);
      // initial
      cb(read<ActiveGame[]>(LS_ACTIVE, []));
      return () => {
        activeListeners.delete(cb);
      };
    },

    subscribeToActiveGame(userId, cb) {
      const handler: Listener<ActiveGame[]> = (games) => {
        cb(games.find((g) => g.userId === userId) ?? null);
      };
      activeListeners.add(handler);
      handler(read<ActiveGame[]>(LS_ACTIVE, []));
      return () => {
        activeListeners.delete(handler);
      };
    },
  };
}
