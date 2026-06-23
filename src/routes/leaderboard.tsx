import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";
import { backend } from "@/services";
import type { GameMode, ScoreEntry } from "@/services/types";

export const Route = createFileRoute("/leaderboard")({
  head: () => ({
    meta: [
      { title: "Leaderboard — Snake Arena" },
      { name: "description", content: "Top scores in walls and pass-through modes." },
    ],
  }),
  component: LeaderboardPage,
});

function LeaderboardPage() {
  const [walls, setWalls] = useState<ScoreEntry[]>([]);
  const [wrap, setWrap] = useState<ScoreEntry[]>([]);

  useEffect(() => {
    let cancel = false;
    const load = async () => {
      const [w, p] = await Promise.all([
        backend.getLeaderboard("walls"),
        backend.getLeaderboard("wrap"),
      ]);
      if (!cancel) {
        setWalls(w);
        setWrap(p);
      }
    };
    load();
    const id = setInterval(load, 3000);
    return () => {
      cancel = true;
      clearInterval(id);
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main className="mx-auto max-w-4xl px-4 py-8">
        <h1 className="text-3xl font-bold tracking-tight">Leaderboard</h1>
        <p className="mt-1 text-sm text-muted-foreground">Best score per player, per mode.</p>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <ScoreTable title="Walls" mode="walls" rows={walls} />
          <ScoreTable title="Pass-through" mode="wrap" rows={wrap} />
        </div>
      </main>
    </div>
  );
}

function ScoreTable({ title, rows }: { title: string; mode: GameMode; rows: ScoreEntry[] }) {
  return (
    <div className="rounded-xl border border-border bg-card p-4">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">No scores yet. Be the first!</p>
      ) : (
        <ol className="space-y-1.5">
          {rows.map((r, i) => (
            <li
              key={r.id}
              className="flex items-center justify-between rounded-md px-2 py-1.5 text-sm odd:bg-muted/40"
            >
              <span className="flex items-center gap-3">
                <span className="w-6 text-right font-mono text-muted-foreground">{i + 1}</span>
                <span className="font-medium">{r.username}</span>
              </span>
              <span className="font-mono tabular-nums">{r.score}</span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
