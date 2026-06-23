import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { SnakeBoard } from "@/components/SnakeBoard";
import { backend } from "@/services";
import type { ActiveGame } from "@/services/types";

export const Route = createFileRoute("/watch/$userId")({
  head: () => ({
    meta: [
      { title: "Spectate — Snake Arena" },
      { name: "description", content: "Watch a live Snake game." },
    ],
  }),
  component: WatchDetail,
});

function WatchDetail() {
  const { userId } = Route.useParams();
  const [game, setGame] = useState<ActiveGame | null>(null);

  useEffect(() => {
    return backend.subscribeToActiveGame(userId, setGame);
  }, [userId]);

  return (
    <div>
      <Link to="/watch" className="text-sm text-muted-foreground hover:text-foreground">
        ← All live games
      </Link>
      {!game ? (
        <div className="mt-6 rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
          This game just ended or hasn't started.
        </div>
      ) : (
        <div className="mt-4 flex flex-col items-center gap-6 md:flex-row md:items-start">
          <SnakeBoard
            width={game.state.width}
            height={game.state.height}
            snake={game.state.snake}
            food={game.state.food}
            alive={game.state.alive}
          />
          <div className="rounded-lg border border-border bg-card p-4">
            <div className="text-lg font-semibold">@{game.username}</div>
            <div className="mt-2 text-xs uppercase text-muted-foreground">Score</div>
            <div className="text-4xl font-bold tabular-nums">{game.score}</div>
            <div className="mt-1 text-xs text-muted-foreground">
              Mode: {game.mode === "walls" ? "Walls" : "Pass-through"}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
