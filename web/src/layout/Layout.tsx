import type { ReactNode } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import alfaMark from '../assets/alfa-mark.svg';
import styles from './Layout.module.css';

type LayoutProps = {
  children: ReactNode;
  actions?: ReactNode;
  navigation?: ReactNode;
};

export function Layout({ children, actions, navigation }: LayoutProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        {/* Логотип ведёт на главную: клиенту — обзор заявок, сотруднику — очередь */}
        <a href='#/' className={styles.brand} aria-label='Альфа-Банк — на главную'>
          <span className={styles.symbol}><img src={alfaMark} alt='' /></span>
        </a>
        {navigation && <nav className={styles.navigation} aria-label='Разделы кабинета'>{navigation}</nav>}
        {actions && <div className={styles.actions}>{actions}</div>}
      </header>

      <main className={styles.main}>{children}</main>

      <footer className={styles.footer}>
        <Typography.Text view='primary-small' color='secondary'>
          Прототип. Данные синтетические
        </Typography.Text>
        <Typography.Text view='primary-small' color='secondary'>Весь процесс — внутри кабинета</Typography.Text>
      </footer>
    </div>
  );
}
