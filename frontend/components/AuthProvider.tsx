/**
 * Contexto de sesión del cliente.
 *
 * Fuente de verdad de "quién es el usuario" en el frontend. Al montar consulta
 * `GET /api/auth/me`; si la cookie httpOnly es válida obtiene el `UserPublic`, y
 * si no (401) queda como anónimo. Expone acciones (`login`, `register`, `logout`,
 * `refresh`) que actualizan el estado en memoria sin recargar la página.
 *
 * El token NUNCA se lee aquí: vive en una cookie httpOnly inaccesible desde JS.
 * El estado local es solo un espejo de conveniencia para pintar la UI.
 */

'use client';

import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';

import * as api from '../lib/api';
import { ApiError } from '../lib/api';
import type { LoginRequest, RegisterRequest, UserPublic } from '../lib/types';

type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

interface AuthContextValue {
  user: UserPublic | null;
  status: AuthStatus;
  login: (req: LoginRequest) => Promise<void>;
  register: (req: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  /** Revalida la sesión contra el backend (p.ej. tras cambios externos). */
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  const refresh = async () => {
    try {
      const me = await api.getMe();
      setUser(me);
      setStatus('authenticated');
    } catch (e) {
      // 401 = no hay sesión válida → anónimo, no es un error real de UI.
      // Cualquier otro fallo (red, 5xx) también lo tratamos como anónimo: sin
      // sesión confirmada, la UI por defecto es la pública.
      if (!(e instanceof ApiError) || e.status !== 401) {
        // Silencioso a propósito: el arranque no debe romper por el backend caído.
      }
      setUser(null);
      setStatus('anonymous');
    }
  };

  // Hidratar la sesión una vez al montar.
  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (req: LoginRequest) => {
    const me = await api.login(req);
    setUser(me);
    setStatus('authenticated');
  };

  const register = async (req: RegisterRequest) => {
    const me = await api.register(req);
    setUser(me);
    setStatus('authenticated');
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      // Pase lo que pase en el servidor, en el cliente ya no hay sesión.
      setUser(null);
      setStatus('anonymous');
    }
  };

  return (
    <AuthContext.Provider value={{ user, status, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de <AuthProvider>');
  return ctx;
}
