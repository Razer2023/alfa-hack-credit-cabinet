import { Link } from '@alfalab/core-components/link';
import { Typography } from '@alfalab/core-components/typography';

import type { Application } from '../api/types';
import styles from './ManagerContact.module.css';

type ManagerContactProps = {
  manager: NonNullable<Application['manager']>;
};

// Кто ведёт заявку и как с ним связаться (S4.9) — шапка чата с менеджером
export function ManagerContact({ manager }: ManagerContactProps) {
  const initials = manager.full_name
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('');
  const tel = manager.phone?.replace(/[^\d+]/g, '');

  return (
    <div className={styles.manager}>
      <span className={styles.avatar} aria-hidden='true'>
        {initials}
      </span>
      <div className={styles.person}>
        <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
          {manager.full_name}
        </Typography.Text>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          {manager.position ?? 'Ваш менеджер'}
        </Typography.Text>
      </div>
      <div className={styles.contacts}>
        {manager.phone && (
          <Typography.Text view='primary-small' tag='p' defaultMargins={false}>
            <Link href={`tel:${tel}`}>{manager.phone}</Link>
          </Typography.Text>
        )}
        {manager.work_hours && (
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            {manager.work_hours}
          </Typography.Text>
        )}
      </div>
    </div>
  );
}
