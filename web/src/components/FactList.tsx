import type { ReactNode } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import styles from './FactList.module.css';

export type Fact = {
  label: string;
  value: ReactNode;
};

type FactListProps = {
  facts: Fact[];
};

// Список «название — значение» для анкеты, условий и проверок
export function FactList({ facts }: FactListProps) {
  return (
    <dl className={styles.list}>
      {facts.map((fact) => (
        <div key={fact.label} className={styles.row}>
          <dt>
            <Typography.Text view='primary-small' color='secondary'>
              {fact.label}
            </Typography.Text>
          </dt>
          <dd className={styles.value}>
            <Typography.Text view='primary-small' tag='div'>
              {fact.value}
            </Typography.Text>
          </dd>
        </div>
      ))}
    </dl>
  );
}
