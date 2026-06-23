export type GameMode = "walls" | "wrap";

export interface User {
  id: string;
  username: string;
}

export interface ScoreEntry {
  id: string;
  userId: string;
  username: string;
  mode: GameMode;
  score: number;
  createdAt: number;
}

export interface ActiveGame {
  userId: string;
  username: string;
  mode: GameMode;
  score: number;
  // serialized snake game state (small): grid size, snake cells, food, dir, alive
  state: {
    width: number;
    height: number;
    snake: Array<[number, number]>;
    food: [number, number];
    dir: "up" | "down" | "left" | "right";
    alive: boolean;
  };
  updatedAt: number;
}

export interface BackendService {
  // auth
  signup(username: string, password: string): Promise<User>;
  login(username: string, password: string): Promise<User>;
  logout(): Promise<void>;
  currentUser(): Promise<User | null>;

  // scores
  submitScore(mode: GameMode, score: number): Promise<ScoreEntry>;
  getLeaderboard(mode: GameMode, limit?: number): Promise<ScoreEntry[]>;

  // active games (spectator)
  publishGameState(state: ActiveGame["state"], mode: GameMode, score: number): Promise<void>;
  endGame(): Promise<void>;
  listActiveGames(): Promise<ActiveGame[]>;
  getActiveGame(userId: string): Promise<ActiveGame | null>;
  subscribeToActiveGames(cb: (games: ActiveGame[]) => void): () => void;
  subscribeToActiveGame(userId: string, cb: (game: ActiveGame | null) => void): () => void;
}
