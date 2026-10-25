import { Typography } from '@alfalab/core-components/typography';

import type { ApplicationEvent } from '../api/types';
import { formatDateTime } from '../format';
import styles from './EventList.module.css';

type EventListProps = {
  events: ApplicationEvent[];
};

// История заявки: новые события сверху
export function EventList({ events: all }: EventListProps) {
  const events = all.filter((event) => event.type !== 'MESSAGE');
  if (events.length === 0) {
    return (
      <Typography.Text view='primary-small' color='secondary'>
        Событий пока нет
      </Typography.Text>
    );
  }
  return (
    <ul className={styles.list}>
      {[...events].reverse().map((event) => (
        <li key={event.id} className={styles.item}>
          <Typography.Text view='primary-small' color='secondary' className={styles.time}>
            {formatDateTime(event.created_at)}
          </Typography.Text>
          <Typography.Text view='primary-small'>{event.message}</Typography.Text>
        </li>
      ))}
    </ul>
  );
}
