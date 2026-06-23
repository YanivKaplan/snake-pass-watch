import { createFileRoute, Link } from "@tanstack/react-router";
import { useCallback, useEffect, useRef, useState } from "react";
import { NavBar } from "@/components/NavBar";
import { SnakeBoard } from "@/components/SnakeBoard";
import { Button } from "@/components/ui/button";
import { createInitialState, step, turn, type Dir, type SnakeState } from "@/game/snake";
import { useAuth } from "@/hooks/useAuth";
import { backend } from "@/services";
import type { GameMode } from "@/services/types";
import messiToilet from "@/assets/messi-toilet.png";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Play — Snake Arena" },
      { name: "description", content: "Play Snake in walls or pass-through mode." },
    ],
  }),
  component: PlayPage,
});

const BOARD = 20;
const TICK_MS = 110;

const KEY_DIR: Record<string, Dir> = {
  ArrowUp: "up",
  ArrowDown: "down",
  ArrowLeft: "left",
  ArrowRight: "right",
  w: "up",
  s: "down",
  a: "left",
  d: "right",
};

function PlayPage() {
  const { user } = useAuth();
  const [mode, setMode] = useState<GameMode>("walls");
  const [state, setState] = useState<SnakeState>(() => createInitialState(BOARD, BOARD, "walls"));
  const [running, setRunning] = useState(false);
  const stateRef = useRef(state);
  stateRef.current = state;
  const submittedRef = useRef(false);

  const reset = useCallback((m: GameMode) => {
    setState(createInitialState(BOARD, BOARD, m));
    setRunning(false);
    submittedRef.current = false;
  }, []);

  useEffect(() => {
    reset(mode);
  }, [mode, reset]);

  // keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const d = KEY_DIR[e.key];
      if (d) {
        e.preventDefault();
        setState((s) => turn(s, d));
      } else if (e.key === " ") {
        e.preventDefault();
        setRunning((r) => !r);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // game loop
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setState((s) => step(s));
    }, TICK_MS);
    return () => clearInterval(id);
  }, [running]);

  // publish active state for spectators + handle death
  useEffect(() => {
    if (!user) return;
    if (state.alive && running) {
      backend.publishGameState(
        {
          width: state.width,
          height: state.height,
          snake: state.snake,
          food: state.food,
          dir: state.dir,
          alive: state.alive,
        },
        state.mode,
        state.score,
      );
    }
    if (!state.alive && !submittedRef.current && state.score > 0) {
      submittedRef.current = true;
      backend.submitScore(state.mode, state.score);
      backend.endGame();
      setRunning(false);
    }
  }, [state, user, running]);

  // end game on unmount
  useEffect(() => {
    return () => {
      backend.endGame();
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <img
          src={messiToilet}
          alt="Messi lifting a golden toilet trophy — Campeones del Mundo"
          className="mb-8 w-full rounded-xl border border-border shadow-lg"
        />
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Snake</h1>
            <p className="text-sm text-muted-foreground">
              Arrow keys or WASD to move. Space to pause.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ModeToggle mode={mode} onChange={setMode} />
          </div>
        </div>

        {!user && (
          <div className="mb-4 rounded-lg border border-border bg-card p-4 text-sm">
            <Link to="/auth" className="font-medium text-primary hover:underline">
              Sign in
            </Link>{" "}
            to save scores and appear on the leaderboard & spectator list.
          </div>
        )}

        <div className="flex flex-col items-center gap-6 md:flex-row md:items-start">
          <SnakeBoard
            width={state.width}
            height={state.height}
            snake={state.snake}
            food={state.food}
            alive={state.alive}
          />

          <div className="flex w-full max-w-xs flex-col gap-3">
            <div className="rounded-lg border border-border bg-card p-4">
              <div className="text-xs uppercase text-muted-foreground">Score</div>
              <div className="text-4xl font-bold tabular-nums">{state.score}</div>
              <div className="mt-1 text-xs text-muted-foreground">
                Mode: {mode === "walls" ? "Walls (deadly)" : "Pass-through (wrap)"}
              </div>
            </div>

            {!state.alive ? (
              <Button onClick={() => reset(mode)} size="lg">
                New game
              </Button>
            ) : (
              <Button onClick={() => setRunning((r) => !r)} size="lg">
                {running ? "Pause" : state.score === 0 ? "Start" : "Resume"}
              </Button>
            )}
            <Button variant="outline" onClick={() => reset(mode)}>
              Reset
            </Button>

            {!state.alive && state.score > 0 && (
              <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-3 text-sm">
                Game over! Final score: <strong>{state.score}</strong>
                {user ? " — saved to leaderboard." : " — sign in to save scores."}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function ModeToggle({ mode, onChange }: { mode: GameMode; onChange: (m: GameMode) => void }) {
  return (
    <div className="inline-flex rounded-md border border-border bg-card p-0.5 text-sm">
      {(["walls", "wrap"] as const).map((m) => (
        <button
          key={m}
          onClick={() => onChange(m)}
          className={
            mode === m
              ? "rounded px-3 py-1.5 bg-primary text-primary-foreground"
              : "rounded px-3 py-1.5 text-muted-foreground hover:text-foreground"
          }
        >
          {m === "walls" ? "Walls" : "Pass-through"}
        </button>
      ))}
    </div>
  );
}
