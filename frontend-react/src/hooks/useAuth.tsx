import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { AxiosError } from 'axios';
import type { ReactNode } from 'react';
import type { User } from '../types';
import { authService } from '../services/api';

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  error: string | null;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<unknown>;
  register: (payload: Parameters<typeof authService.register>[0]) => Promise<unknown>;
  updateProfile: (payload: Partial<User>) => Promise<User>;
  logout: () => void;
  checkAuth: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('pizzeria_auth_token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await authService.me();
      setUser(userData);
      setError(null);
    } catch {
      authService.logout();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await authService.login(email, password);
      setUser(response.user);
      return response;
    } catch (err: unknown) {
      let message = 'Login failed';
      if (err instanceof AxiosError && err.response?.data?.detail) {
        message = err.response.data.detail;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (payload: Parameters<typeof authService.register>[0]) => {
    setLoading(true);
    setError(null);
    try {
      const response = await authService.register(payload);
      setUser(response.user);
      return response;
    } catch (err: unknown) {
      let message = 'Registration failed';
      if (err instanceof AxiosError && err.response?.data?.detail) {
        message = err.response.data.detail;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateProfile = useCallback(async (payload: Partial<User>) => {
    setLoading(true);
    setError(null);
    try {
      const updatedUser = await authService.updateProfile(payload);
      setUser(updatedUser);
      return updatedUser;
    } catch (err: unknown) {
      let message = 'Update failed';
      if (err instanceof AxiosError && err.response?.data?.detail) {
        message = err.response.data.detail;
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
    setError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      isAuthenticated: !!user,
      isAdmin: user?.is_admin ?? false,
      login,
      register,
      updateProfile,
      logout,
      checkAuth,
    }),
    [user, loading, error, login, register, updateProfile, logout, checkAuth]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
