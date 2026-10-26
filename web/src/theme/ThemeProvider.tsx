import { type ReactNode, useCallback, useEffect, useLayoutEffect, useMemo, useState } from 'react';

import { type Theme, ThemeContext } from './ThemeContext';

const SYSTEM_DARK = '(prefers-color-scheme: dark)';

function systemTheme(): Theme {
  return window.matchMedia?.(SYSTEM_DARK).matches ? 'dark' : 'light';
}

// Светлая и тёмная тема кабинета. Тёмная — themes/dark.css дизайн-системы на :root[data-theme="dark"] (index.css).
// При открытии тема — как в системе компьютера; пока пользователь не переключил её сам, она меняется вместе с системой.
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(systemTheme);
  const [manual, setManual] = useState(false);

  // До отрисовки, чтобы страница не мигала светлой темой
  useLayoutEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (manual || !window.matchMedia) return;
    const query = window.matchMedia(SYSTEM_DARK);
    const follow = () => setTheme(query.matches ? 'dark' : 'light');
    query.addEventListener('change', follow);
    return () => query.removeEventListener('change', follow);
  }, [manual]);

  const toggle = useCallback(() => {
    setManual(true);
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  }, []);
  const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
