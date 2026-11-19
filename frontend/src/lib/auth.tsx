import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { api } from "./api";
import type { UserPublic } from "./types";

interface AuthContextValue {
  user: UserPublic | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("mz_access_token");
    if (!token) {
      setIsLoading(false);
      return;
    }
    api
      .get<UserPublic>("/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => {
        localStorage.removeItem("mz_access_token");
        localStorage.removeItem("mz_refresh_token");
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("mz_access_token", data.access_token);
    localStorage.setItem("mz_refresh_token", data.refresh_token);
    const me = await api.get<UserPublic>("/auth/me");
    setUser(me.data);
  }

  function logout() {
    localStorage.removeItem("mz_access_token");
    localStorage.removeItem("mz_refresh_token");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé à l'intérieur de <AuthProvider>");
  return ctx;
}
