import { create } from "zustand";
import { apiFetch } from "@/lib/api";
import { setTokens, clearTokens, getAccessToken } from "@/lib/auth";

interface User {
  id: string;
  email: string;
  phone: string;
  full_name: string;
  firm_name: string | null;
  is_active: boolean;
  is_verified: boolean;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    phone: string;
    password: string;
    full_name: string;
    firm_name?: string;
  }) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,

  login: async (email, password) => {
    const data = await apiFetch<{
      access_token: string;
      refresh_token: string;
    }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
      skipAuth: true,
    });
    setTokens(data.access_token, data.refresh_token);
    const user = await apiFetch<User>("/auth/me");
    set({ user, isAuthenticated: true, isLoading: false });
  },

  register: async (data) => {
    const tokens = await apiFetch<{
      access_token: string;
      refresh_token: string;
    }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
      skipAuth: true,
    });
    setTokens(tokens.access_token, tokens.refresh_token);
    const user = await apiFetch<User>("/auth/me");
    set({ user, isAuthenticated: true, isLoading: false });
  },

  logout: () => {
    clearTokens();
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  fetchUser: async () => {
    const token = getAccessToken();
    if (!token) {
      set({ user: null, isAuthenticated: false, isLoading: false });
      return;
    }
    try {
      const user = await apiFetch<User>("/auth/me");
      set({ user, isAuthenticated: true, isLoading: false });
    } catch {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
