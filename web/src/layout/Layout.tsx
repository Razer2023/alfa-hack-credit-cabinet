import type { ReactNode } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import alfaMark from '../assets/alfa-mark.svg';
import { useInvertedOnDark, useTheme } from '../theme/ThemeContext';
import styles from './Layout.module.css';

export type Tone = 'dark' | 'light';

type LayoutProps = {
  children: ReactNode;
  actions?: ReactNode;
  navigation?: ReactNode;
  // dark — тёмная шапка над первым экраном (обзор и кредиты клиента), light — все остальные экраны
  tone?: Tone;
  // Страница сама раскладывает тёмный первый экран и белый лист (см. Page.tsx), без общего контейнера
  bleed?: boolean;
};

export function Layout({ children, actions, navigation, tone = 'light', bleed = false }: LayoutProps) {
  const dark = tone === 'dark';
  return (
    <div className={styles.page}>
      <header className={dark ? `${styles.header} ${styles.dark} dark-surface` : styles.header}>
        <div className={styles.bar}>
          {/* Логотип ведёт на главную: клиенту — обзор заявок, сотруднику — очередь */}
          <a href='#/' className={styles.brand} aria-label='Кредитный кабинет — на главную'>
            <span className={styles.symbol}><img src={alfaMark} alt='' /></span>
            <Typography.Text className={styles.tagline} view='primary-small' color={dark ? 'secondary-inverted' : 'secondary'}>
              для бизнеса
            </Typography.Text>
          </a>
          {navigation && <nav className={styles.navigation} aria-label='Разделы кабинета'>{navigation}</nav>}
          <div className={styles.actions}>
            {actions}
            <ThemeToggle tone={tone} />
          </div>
        </div>
      </header>

      <main className={bleed ? styles.bleed : styles.main}>{children}</main>

      <footer className={`${styles.footer} dark-surface`}>
        <div className={styles.footerBar}>
          <Typography.Text view='primary-small' color='secondary-inverted'>
            Прототип. Данные синтетические
          </Typography.Text>
          <Typography.Text view='primary-small' color='secondary-inverted'>Весь процесс — внутри кабинета</Typography.Text>
        </div>
      </footer>
    </div>
  );
}

// Переключатель светлой и тёмной темы — в шапке на всех экранах, включая вход
function ThemeToggle({ tone }: { tone: Tone }) {
  const { theme, toggle } = useTheme();
  const inverted = useInvertedOnDark() && tone === 'dark';
  const next = theme === 'dark' ? 'Светлая тема' : 'Тёмная тема';
  return (
    <Button view='transparent' colors={inverted ? 'inverted' : 'default'} size={40} onClick={toggle}
      aria-label={`Включить: ${next.toLowerCase()}`}>
      {next}
    </Button>
  );
}

type NavLinkProps = {
  href: string;
  current: boolean;
  tone: Tone;
  children: ReactNode;
};

// Раздел в шапке: подчёркнутая вкладка, как в макете «Кабинет — клиент v2»
export function NavLink({ href, current, tone, children }: NavLinkProps) {
  const className = current ? `${styles.navLink} ${styles.navCurrent}` : styles.navLink;
  const color = tone === 'dark' ? (current ? 'primary-inverted' : 'secondary-inverted') : current ? 'primary' : 'secondary';
  return (
    <a href={href} className={className} aria-current={current ? 'page' : undefined}>
      <Typography.Text view='primary-medium' weight='medium' color={color}>{children}</Typography.Text>
    </a>
  );
}
