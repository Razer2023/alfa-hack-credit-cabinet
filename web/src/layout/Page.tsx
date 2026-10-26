import type { ReactNode } from 'react';

import styles from './Page.module.css';

type SlotProps = {
  children: ReactNode;
  className?: string;
};

// Тёмный первый экран под тёмной шапкой (обзор и кредиты клиента)
export function Hero({ children, className }: SlotProps) {
  return (
    <div className={`${styles.hero} dark-surface`}>
      <div className={className ? `${styles.container} ${className}` : styles.container}>{children}</div>
    </div>
  );
}

// Белый лист со скруглением, который наезжает на тёмный первый экран
export function Sheet({ children, className }: SlotProps) {
  return (
    <div className={styles.sheet}>
      <div className={className ? `${styles.container} ${className}` : styles.container}>{children}</div>
    </div>
  );
}
