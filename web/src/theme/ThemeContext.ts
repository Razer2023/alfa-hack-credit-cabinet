import { createContext, useContext } from 'react';

export type Theme = 'light' | 'dark';

export type ThemeState = {
  theme: Theme;
  toggle: () => void;
};

export const ThemeContext = createContext<ThemeState | null>(null);

export function useTheme(): ThemeState {
  const theme = useContext(ThemeContext);
  if (!theme) throw new Error('useTheme вызван вне ThemeProvider');
  return theme;
}

/**
 * Тёмные поверхности (тёмная шапка, первый экран, аналитика) в светлой теме рисуются инвертированными
 * цветами: кнопкам на них нужен colors='inverted'. В тёмной теме вся страница тёмная — обычные цвета.
 */
export function useInvertedOnDark(): boolean {
  return useTheme().theme === 'light';
}
