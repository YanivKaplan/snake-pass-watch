import { describe, expect, it } from "vitest";
import { createInitialState, step, turn } from "./snake";

const rand = () => 0; // deterministic

describe("snake game logic", () => {
  it("creates a starting state", () => {
    const s = createInitialState(10, 10, "walls");
    expect(s.snake.length).toBe(3);
    expect(s.alive).toBe(true);
    expect(s.score).toBe(0);
  });

  it("moves forward each step", () => {
    let s = createInitialState(10, 10, "walls");
    const [hx, hy] = s.snake[0];
    s = step(s, rand);
    expect(s.snake[0]).toEqual([hx + 1, hy]);
  });

  it("dies on wall in walls mode", () => {
    let s = createInitialState(5, 5, "walls");
    for (let i = 0; i < 10; i++) s = step(s, rand);
    expect(s.alive).toBe(false);
  });

  it("wraps around in wrap mode", () => {
    let s = createInitialState(5, 5, "wrap");
    for (let i = 0; i < 20; i++) s = step(s, rand);
    expect(s.alive).toBe(true);
  });

  it("ignores reverse direction", () => {
    let s = createInitialState(10, 10, "walls");
    s = turn(s, "left"); // currently moving right
    s = step(s, rand);
    expect(s.dir).toBe("right");
  });

  it("grows when eating food", () => {
    let s = createInitialState(10, 10, "wrap");
    // place food right in front of head
    const [hx, hy] = s.snake[0];
    s = { ...s, food: [hx + 1, hy] };
    const before = s.snake.length;
    s = step(s, rand);
    expect(s.snake.length).toBe(before + 1);
    expect(s.score).toBe(1);
  });
});
