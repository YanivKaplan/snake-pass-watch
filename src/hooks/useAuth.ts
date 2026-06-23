import { useCallback, useEffect, useState } from "react";
import { backend } from "@/services";
import type { User } from "@/services/types";

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const u = await backend.currentUser();
    setUser(u);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const onStorage = () => refresh();
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [refresh]);

  return {
    user,
    loading,
    login: async (u: string, p: string) => {
      const r = await backend.login(u, p);
      setUser(r);
      return r;
    },
    signup: async (u: string, p: string) => {
      const r = await backend.signup(u, p);
      setUser(r);
      return r;
    },
    logout: async () => {
      await backend.logout();
      setUser(null);
    },
  };
}
