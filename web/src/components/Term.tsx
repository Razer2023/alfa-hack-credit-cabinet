import type { ReactNode } from 'react';
import { Tooltip } from '@alfalab/core-components/tooltip';

import { useUser } from '../auth/AuthContext';
import { GLOSSARY } from '../glossary';
import styles from './Term.module.css';

type TermProps = {
  // Подпись из словаря; по умолчанию — текст внутри
  name?: string;
  children: ReactNode;
};

// Термин с подсказкой по клику (S3.5). На телефоне подсказка открывается шторкой снизу.
// Сотрудникам банка термины знакомы — у них текст без подсказки.
export function Term({ name, children }: TermProps) {
  const user = useUser();
  const key = name ?? (typeof children === 'string' ? children : '');
  const hint = GLOSSARY[key];
  if (!hint || user.role !== 'CLIENT') return <>{children}</>;

  return (
    <Tooltip
      content={hint}
      trigger='click'
      position='top'
      view='hint'
      targetTag='span'
      actionButtonTitle='Понятно'
      contentClassName={styles.content}
    >
      <button type='button' className={styles.term} aria-label={`${key}: что это`}>
        {children}
      </button>
    </Tooltip>
  );
}
