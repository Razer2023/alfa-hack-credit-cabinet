import { useState } from 'react';
import { Notification } from '@alfalab/core-components/notification';

import type { ApplicationEvent } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { useApplicationEvents } from '../events';

// Уведомления внутри продукта вместо SMS и почты: клиенту — что сделал банк, банку — новые заявки на решение
export function EventToast() {
  const user = useUser();
  const [event, setEvent] = useState<ApplicationEvent | null>(null);

  useApplicationEvents((incoming) => {
    const interesting =
      user.role === 'CLIENT'
        ? incoming.type === 'STATUS_CHANGED' && incoming.actor_role !== 'CLIENT'
        : incoming.to_status === 'MANUAL_REVIEW';
    if (interesting) setEvent(incoming);
  });

  const badge =
    event?.to_status === 'REJECTED'
      ? 'negative-alert'
      : event?.to_status === 'NEED_INFO' || event?.to_status === 'MANUAL_REVIEW'
        ? 'attention-alert'
        : 'positive-checkmark';

  return (
    <Notification
      visible={event !== null}
      title={user.role === 'CLIENT' ? 'Заявка обновлена' : 'Новая заявка на решение'}
      badge={badge}
      autoCloseDelay={5000}
      hasCloser={true}
      onClose={() => setEvent(null)}
      onCloseTimeout={() => setEvent(null)}
    >
      {event?.message}
    </Notification>
  );
}
