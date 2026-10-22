import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import { Spinner } from '@alfalab/core-components/spinner';

import { api, getToken, setToken, setUnauthorizedHandler } from '../api/client';
import type { Token, User } from '../api/types';
import { AuthContext } from './AuthContext';

type AuthProviderProps = {
  children: ReactNode;
};

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  // Токен из прошлого визита проверяем запросом /me, до этого ничего не показываем
  const [restoring, setRestoring] = useState(() => getToken() !== null);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    if (!getToken()) return;
    api<User>('/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setRestoring(false));
  }, []);

  const login = useCallback(async (loginName: string, password: string) => {
    const token = await api<Token>('/auth/login', { method: 'POST', body: { login: loginName, password } });
    setToken(token.access_token);
    setUser(token.user);
  }, []);

  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);

  if (restoring) return <Spinner preset={48} visible={true} />;
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
