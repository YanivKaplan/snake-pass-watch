import { createFileRoute, Link, Outlet, useMatchRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { NavBar } from "@/components/NavBar";
import { backend } from "@/services";
import type { ActiveGame } from "@/services/types";

export const Route = createFileRoute("/watch")({
  head: () => ({
    meta: [
      { title: "Watch — Snake Arena" },
      { name: "description", content: "Spectate live Snake games." },
    ],
  }),
  component: WatchLayout,
});

function WatchLayout() {
  const [games, setGames] = useState<ActiveGame[]>([]);
  const matchRoute = useMatchRoute();
  const onDetail = matchRoute({ to: "/watch/$userId" });

  useEffect(() => {
    return backend.subscribeToActiveGames(setGames);
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <NavBar />
      <main className="mx-auto max-w-5xl px-4 py-8">
        <h1 className="text-3xl font-bold tracking-tight">Live games</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Watch other players in real time.
        </p>

        {onDetail ? (
          <div className="mt-6">
            <Outlet />
          </div>
        ) : (
          <div className="mt-6">
            {games.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-8 text-center text-sm text-muted-foreground">
                No one is playing right now. Start a game to appear here.
              </div>
            ) : (
              <ul className="grid gap-3 sm:grid-cols-2">
                {games.map((g) => (
                  <li key={g.userId}>
                    <Link
                      to="/watch/$userId"
                      params={{ userId: g.userId }}
                      className="flex items-center justify-between rounded-lg border border-border bg-card p-4 transition-colors hover:bg-accent"
                    >
                      <div>
                        <div className="font-semibold">@{g.username}</div>
                        <div className="text-xs text-muted-foreground">
                          {g.mode === "walls" ? "Walls" : "Pass-through"} · score {g.score}
                        </div>
                      </div>
                      <span className="text-sm text-primary">Watch →</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
