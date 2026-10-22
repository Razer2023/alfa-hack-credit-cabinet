import { useSyncExternalStore } from 'react';

// Простой роутер на hash: отдельная библиотека для пяти экранов не нужна,
// а nginx и Vite отдают index.html на любой путь без настройки.
function subscribe(callback: () => void) {
  window.addEventListener('hashchange', callback);
  return () => window.removeEventListener('hashchange', callback);
}

function currentPath(): string {
  return window.location.hash.replace(/^#/, '') || '/';
}

export function useRoute(): string {
  return useSyncExternalStore(subscribe, currentPath);
}

export function navigate(path: string) {
  window.location.hash = path;
}

/** '/applications/:id' и '/applications/42' → { id: '42' }, иначе null. */
export function matchRoute(pattern: string, path: string): Record<string, string> | null {
  const expected = pattern.split('/');
  const actual = path.split('/');
  if (expected.length !== actual.length) return null;
  const params: Record<string, string> = {};
  for (let i = 0; i < expected.length; i += 1) {
    if (expected[i].startsWith(':')) params[expected[i].slice(1)] = decodeURIComponent(actual[i]);
    else if (expected[i] !== actual[i]) return null;
  }
  return params;
}
