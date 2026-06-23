import { Link } from "@tanstack/react-router";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

export function NavBar() {
  const { user, logout } = useAuth();
  return (
    <header className="border-b border-border bg-card/60 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link to="/" className="text-lg font-bold tracking-tight">
          🐍 Snake Arena
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          <Link
            to="/"
            className="rounded-md px-3 py-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
            activeProps={{ className: "rounded-md px-3 py-1.5 bg-accent text-foreground" }}
          >
            Play
          </Link>
          <Link
            to="/leaderboard"
            className="rounded-md px-3 py-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
            activeProps={{ className: "rounded-md px-3 py-1.5 bg-accent text-foreground" }}
          >
            Leaderboard
          </Link>
          <Link
            to="/watch"
            className="rounded-md px-3 py-1.5 text-muted-foreground hover:bg-accent hover:text-foreground"
            activeProps={{ className: "rounded-md px-3 py-1.5 bg-accent text-foreground" }}
          >
            Watch
          </Link>
          {user ? (
            <div className="ml-3 flex items-center gap-2">
              <span className="text-xs text-muted-foreground">@{user.username}</span>
              <Button size="sm" variant="outline" onClick={() => logout()}>
                Log out
              </Button>
            </div>
          ) : (
            <Link
              to="/auth"
              className="ml-3 rounded-md bg-primary px-3 py-1.5 text-primary-foreground hover:bg-primary/90"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
