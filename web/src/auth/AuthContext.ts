import { createContext, useContext } from 'react';

import type { User } from '../api/types';

export type AuthState = {
  user: User | null;
  login: (login: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth вызван вне AuthProvider');
  return auth;
}

/** Пользователь точно вошёл: экраны кабинета показываются только после входа. */
export function useUser(): User {
  const { user } = useAuth();
  if (!user) throw new Error('useUser вызван до входа');
  return user;
}
