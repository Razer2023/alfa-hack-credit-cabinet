import { useEffect, useRef } from 'react';

import { eventStreamUrl } from './api/client';
import type { ApplicationEvent } from './api/types';

// Одно SSE-соединение на всё приложение: App открывает поток, экраны подписываются через useApplicationEvents.
const EVENT_NAME = 'credit-cabinet:event';

export function openEventStream(token: string): () => void {
  const source = new EventSource(eventStreamUrl(token));
  // Обрыв браузер переподключает сам и догоняет пропущенное по Last-Event-ID
  source.addEventListener('application', (message) => {
    const event = JSON.parse((message as MessageEvent<string>).data) as ApplicationEvent;
    window.dispatchEvent(new CustomEvent<ApplicationEvent>(EVENT_NAME, { detail: event }));
  });
  return () => source.close();
}

export function useApplicationEvents(onEvent: (event: ApplicationEvent) => void) {
  const handler = useRef(onEvent);
  useEffect(() => {
    handler.current = onEvent;
  });

  useEffect(() => {
    const listener = (event: Event) => handler.current((event as CustomEvent<ApplicationEvent>).detail);
    window.addEventListener(EVENT_NAME, listener);
    return () => window.removeEventListener(EVENT_NAME, listener);
  }, []);
}
