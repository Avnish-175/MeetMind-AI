import { create } from 'zustand';
import {
  extractAuthErrorMessage,
  fetchCurrentUser,
  loginUser,
  registerUser,
} from '../services/authApi';
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from '../services/tokenStorage';
import type { AuthUser, LoginRequest, RegisterRequest } from '../types/auth';

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitializing: boolean;
  error: string | null;
  initializeAuth: () => Promise<void>;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => void;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: getAccessToken(),
  isAuthenticated: false,
  isLoading: false,
  isInitializing: true,
  error: null,

  initializeAuth: async () => {
    const token = getAccessToken();
    if (!token) {
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isInitializing: false,
      });
      return;
    }

    set({ isInitializing: true, accessToken: token });
    try {
      const user = await fetchCurrentUser();
      set({
        user,
        accessToken: token,
        isAuthenticated: true,
        isInitializing: false,
        error: null,
      });
    } catch {
      clearAccessToken();
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isInitializing: false,
      });
    }
  },

  login: async (payload: LoginRequest) => {
    set({ isLoading: true, error: null });
    try {
      const tokenData = await loginUser(payload);
      setAccessToken(tokenData.access_token);
      const user = await fetchCurrentUser();
      set({
        user,
        accessToken: tokenData.access_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      clearAccessToken();
      const message = extractAuthErrorMessage(err);
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: message,
      });
      throw new Error(message);
    }
  },

  register: async (payload: RegisterRequest) => {
    set({ isLoading: true, error: null });
    try {
      await registerUser(payload);
      const tokenData = await loginUser({
        email: payload.email,
        password: payload.password,
      });
      setAccessToken(tokenData.access_token);
      const user = await fetchCurrentUser();
      set({
        user,
        accessToken: tokenData.access_token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err) {
      clearAccessToken();
      const message = extractAuthErrorMessage(err);
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        isLoading: false,
        error: message,
      });
      throw new Error(message);
    }
  },

  logout: () => {
    clearAccessToken();
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
    });
  },

  clearError: () => set({ error: null }),
}));
