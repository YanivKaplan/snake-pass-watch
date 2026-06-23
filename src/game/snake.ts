import type { GameMode } from "@/services/types";

export type Dir = "up" | "down" | "left" | "right";
export type Cell = [number, number];

export interface SnakeState {
  width: number;
  height: number;
  snake: Cell[]; // head is index 0
  dir: Dir;
  pendingDir: Dir;
  food: Cell;
  alive: boolean;
  score: number;
  mode: GameMode;
}

const OPPOSITE: Record<Dir, Dir> = { up: "down", down: "up", left: "right", right: "left" };

export function createInitialState(width: number, height: number, mode: GameMode): SnakeState {
  const cx = Math.floor(width / 2);
  const cy = Math.floor(height / 2);
  const snake: Cell[] = [
    [cx, cy],
    [cx - 1, cy],
    [cx - 2, cy],
  ];
  return {
    width,
    height,
    snake,
    dir: "right",
    pendingDir: "right",
    food: spawnFood(width, height, snake, () => Math.random()),
    alive: true,
    score: 0,
    mode,
  };
}

export function spawnFood(
  width: number,
  height: number,
  snake: Cell[],
  rand: () => number,
): Cell {
  const occupied = new Set(snake.map(([x, y]) => `${x},${y}`));
  const free: Cell[] = [];
  for (let x = 0; x < width; x++) {
    for (let y = 0; y < height; y++) {
      if (!occupied.has(`${x},${y}`)) free.push([x, y]);
    }
  }
  if (free.length === 0) return [0, 0];
  return free[Math.floor(rand() * free.length)];
}

export function turn(state: SnakeState, dir: Dir): SnakeState {
  if (OPPOSITE[dir] === state.dir && state.snake.length > 1) return state;
  return { ...state, pendingDir: dir };
}

export function step(state: SnakeState, rand: () => number = Math.random): SnakeState {
  if (!state.alive) return state;
  const dir = state.pendingDir;
  const [hx, hy] = state.snake[0];
  let nx = hx;
  let ny = hy;
  if (dir === "up") ny -= 1;
  else if (dir === "down") ny += 1;
  else if (dir === "left") nx -= 1;
  else nx += 1;

  if (state.mode === "wrap") {
    nx = (nx + state.width) % state.width;
    ny = (ny + state.height) % state.height;
  } else if (nx < 0 || ny < 0 || nx >= state.width || ny >= state.height) {
    return { ...state, dir, alive: false };
  }

  const ate = nx === state.food[0] && ny === state.food[1];
  const newSnake: Cell[] = [[nx, ny], ...state.snake];
  if (!ate) newSnake.pop();

  // self collision (after move). Check against newSnake tail (skip head).
  for (let i = 1; i < newSnake.length; i++) {
    if (newSnake[i][0] === nx && newSnake[i][1] === ny) {
      return { ...state, dir, alive: false, snake: newSnake };
    }
  }

  const food = ate ? spawnFood(state.width, state.height, newSnake, rand) : state.food;
  return {
    ...state,
    dir,
    snake: newSnake,
    food,
    score: ate ? state.score + 1 : state.score,
  };
}
