import React, { createContext, useContext, useEffect, useState } from "react";

type User = { email: string; token: string };

interface AuthContextType {
  currentUser: User | null;
  loading: boolean;
  login: (email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  currentUser: null,
  loading: true,
  login: async () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

const AUTH_STORAGE_KEY = "auth.user";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      // Hydrate from localStorage
      const raw = localStorage.getItem(AUTH_STORAGE_KEY);
      if (raw) {
        const user = JSON.parse(raw) as User;
        if (user?.email && user?.token) setCurrentUser(user);
      }
    } catch {
      // ignore
    }
    setLoading(false);
  }, []);

  async function login(email: string) {
    const apiUrl = import.meta.env.VITE_API_URL || "";

    const response = await fetch(`${apiUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(text || `Login failed (${response.status})`);
    }

    const data = (await response.json()) as { token: string };
    const user: User = { email, token: data.token };

    setCurrentUser(user);
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
  }

  function logout() {
    setCurrentUser(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }

  const value: AuthContextType = { currentUser, loading, login, logout };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}
