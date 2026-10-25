import type { ReactNode } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import styles from './FactList.module.css';
import { Term } from './Term';

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
              <Term>{fact.label}</Term>
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
