import type { ErrorOut } from './types';

// Адрес всегда относительный: в разработке /api проксирует Vite, в Docker — nginx.
const BASE = '/api/v1';
const TOKEN_KEY = 'credit-cabinet.token';

/** Ошибка API. message написан ядром для человека — его можно показывать как есть. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

let onUnauthorized: () => void = () => {};

export function setUnauthorizedHandler(handler: () => void) {
  onUnauthorized = handler;
}

// sessionStorage может быть недоступен (приватный режим), поэтому каждое обращение — в try
export function getToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) sessionStorage.setItem(TOKEN_KEY, token);
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // без хранилища вход просто не переживёт перезагрузку страницы
  }
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PATCH';
  body?: unknown;
};

export async function api<T>(path: string, { method = 'GET', body }: RequestOptions = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  let response: Response;
  try {
    response = await fetch(BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'network', 'Нет связи с сервером. Проверьте подключение и попробуйте ещё раз');
  }

  if (response.status === 401 && token) onUnauthorized();
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as Partial<ErrorOut> | null;
    const fallback = response.status === 422 ? 'Проверьте введённые данные' : 'Что-то пошло не так, попробуйте ещё раз';
    throw new ApiError(response.status, error?.code ?? 'error', error?.message ?? fallback);
  }
  return (await response.json()) as T;
}

/** Загрузка файла: тело — сам файл, имя — в заголовке X-Filename (S4.7). */
export async function apiUpload<T>(path: string, file: File): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    'Content-Type': file.type || 'application/octet-stream',
    'X-Filename': encodeURIComponent(file.name),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  let response: Response;
  try {
    response = await fetch(BASE + path, { method: 'POST', headers, body: file });
  } catch {
    throw new ApiError(0, 'network', 'Нет связи с сервером. Проверьте подключение и попробуйте ещё раз');
  }
  if (response.status === 401 && token) onUnauthorized();
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as Partial<ErrorOut> | null;
    throw new ApiError(response.status, error?.code ?? 'error', error?.message ?? 'Не удалось загрузить файл');
  }
  return (await response.json()) as T;
}

/** Скачать файл с авторизацией и отдать его браузеру. */
export async function apiDownload(path: string, fallbackName: string): Promise<void> {
  const token = getToken();
  const response = await fetch(BASE + path, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!response.ok) throw new ApiError(response.status, 'download', 'Не удалось скачать файл');
  const disposition = response.headers.get('content-disposition') ?? '';
  const encoded = /filename\*=UTF-8''([^;]+)/.exec(disposition)?.[1];
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement('a');
  link.href = url;
  link.download = encoded ? decodeURIComponent(encoded) : fallbackName;
  link.click();
  URL.revokeObjectURL(url);
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : 'Что-то пошло не так, попробуйте ещё раз';
}

/** Поток событий ядра (SSE). EventSource не умеет заголовки, поэтому токен — в параметре. */
export function eventStreamUrl(token: string): string {
  return `${BASE}/stream?token=${encodeURIComponent(token)}`;
}
