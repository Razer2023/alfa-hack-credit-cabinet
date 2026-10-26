import type { ReactNode } from 'react';
import { Typography, type TextProps } from '@alfalab/core-components/typography';

import type { ApplicationStatus, StatusOut } from '../api/types';
import styles from './StatusDot.module.css';

export type DotTone = 'positive' | 'attention' | 'negative' | 'muted' | 'neutral';

const TONE: Record<ApplicationStatus, DotTone> = {
  DRAFT: 'muted',
  SUBMITTED: 'neutral',
  CHECKING: 'neutral',
  NEED_INFO: 'attention',
  SCORING: 'neutral',
  PENDING_APPROVAL: 'neutral',
  MANUAL_REVIEW: 'neutral',
  APPROVED: 'positive',
  COUNTER_OFFER: 'attention',
  REJECTED: 'negative',
  SIGNED: 'positive',
  ISSUED: 'positive',
  CANCELLED: 'muted',
};

type DotLabelProps = {
  tone: DotTone;
  children: ReactNode;
  // inverted — на тёмном первом экране
  inverted?: boolean;
  view?: TextProps['view'];
};

// Подпись с цветной точкой: статус заявки, шансы предоценки, «подходит лучше всего»
export function DotLabel({ tone, children, inverted = false, view = 'primary-small' }: DotLabelProps) {
  const dot = [styles.dot, styles[tone], inverted && styles.inverted].filter(Boolean).join(' ');
  return (
    <Typography.Text
      className={styles.status}
      view={view}
      weight='medium'
      color={inverted ? 'primary-inverted' : tone === 'muted' ? 'secondary' : 'primary'}
    >
      <span className={dot} aria-hidden='true' />
      {children}
    </Typography.Text>
  );
}

type StatusDotProps = Omit<DotLabelProps, 'tone' | 'children'> & {
  status: StatusOut;
};

// Статус клиентской заявки: название из API (status.title), здесь только цвет точки
export function StatusDot({ status, ...props }: StatusDotProps) {
  return <DotLabel tone={TONE[status.code]} {...props}>{status.title}</DotLabel>;
}
