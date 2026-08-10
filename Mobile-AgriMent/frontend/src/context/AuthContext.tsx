import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { User } from "../types";
import { authService } from "../services/auth";
import { setAuthFailureHandler } from "../services/api";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string,
    region: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadStoredUser();

    // If any API call fails authentication (401 or 403 "Not authenticated"),
    // drop the in-memory user so the app returns to the Login screen instead of
    // staying stuck in a broken "logged in" state.
    setAuthFailureHandler(() => {
      setUser(null);
    });

    return () => setAuthFailureHandler(null);
  }, []);

  const loadStoredUser = async () => {
    try {
      const token = await authService.getStoredToken();
      if (token) {
        const storedUser = await authService.getStoredUser();
        if (storedUser) {
          setUser(storedUser);
        }
      }
    } catch {
      await authService.logout();
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    const response = await authService.login(email, password);
    setUser(response.user);
  };

  const register = async (
    name: string,
    email: string,
    password: string,
    region: string
  ) => {
    const response = await authService.register(
      name,
      email,
      password,
      region as any
    );
    setUser(response.user);
  };

  const logout = async () => {
    await authService.logout();
    setUser(null);
  };

  const refreshUser = async () => {
    const storedUser = await authService.getStoredUser();
    if (storedUser) setUser(storedUser);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
