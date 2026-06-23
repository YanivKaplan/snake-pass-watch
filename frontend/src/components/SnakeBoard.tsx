import { useMemo } from "react";
import type { Cell } from "@/game/snake";

interface Props {
  width: number;
  height: number;
  snake: Cell[];
  food: Cell;
  alive: boolean;
  cellSize?: number;
}

export function SnakeBoard({ width, height, snake, food, alive, cellSize = 22 }: Props) {
  const snakeSet = useMemo(() => new Set(snake.map(([x, y]) => `${x},${y}`)), [snake]);
  const headKey = snake.length ? `${snake[0][0]},${snake[0][1]}` : "";
  const foodKey = `${food[0]},${food[1]}`;

  return (
    <div
      className="inline-grid rounded-lg border border-border bg-card p-2 shadow-sm"
      style={{
        gridTemplateColumns: `repeat(${width}, ${cellSize}px)`,
        gridTemplateRows: `repeat(${height}, ${cellSize}px)`,
        gap: 1,
      }}
      role="grid"
      aria-label="Snake board"
    >
      {Array.from({ length: width * height }).map((_, i) => {
        const x = i % width;
        const y = Math.floor(i / width);
        const k = `${x},${y}`;
        const isHead = k === headKey;
        const isSnake = snakeSet.has(k);
        const isFood = k === foodKey;
        return (
          <div
            key={k}
            className={
              isHead
                ? alive
                  ? "rounded-sm bg-primary"
                  : "rounded-sm bg-destructive"
                : isSnake
                  ? "rounded-sm bg-primary/70"
                  : isFood
                    ? "rounded-full bg-accent-foreground"
                    : "rounded-sm bg-muted"
            }
          />
        );
      })}
    </div>
  );
}
