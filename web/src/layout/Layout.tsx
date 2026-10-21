import type { ReactNode } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import styles from './Layout.module.css';

type LayoutProps = {
  children: ReactNode;
};

export function Layout({ children }: LayoutProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Typography.Title tag='div' view='small' font='system' weight='bold'>
          Кредитный кабинет
        </Typography.Title>
        <Typography.Text view='primary-small' color='secondary'>
          для малого и микробизнеса
        </Typography.Text>
      </header>

      <main className={styles.main}>{children}</main>

      <footer className={styles.footer}>
        <Typography.Text view='primary-small' color='secondary'>
          Прототип. Данные синтетические
        </Typography.Text>
      </footer>
    </div>
  );
}
