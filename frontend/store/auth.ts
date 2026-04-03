import { create } from "zustand";
import { persist } from "zustand/middleware";

type AuthState = {
  token: string | null;
  userId: number | null;
  username: string | null;
  setToken: (token: string | null) => void;
  setAuth: (token: string, userId: number, username: string) => void;
  logout: () => void;
};

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      userId: null,
      username: null,
      setToken: (token) => set({ token }),
      setAuth: (token, userId, username) =>
        set({ token, userId, username }),
      logout: () => set({ token: null, userId: null, username: null }),
    }),
    {
      name: "auth-storage",
    }
  )
);

