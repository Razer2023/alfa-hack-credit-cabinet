import type { ReactNode } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import { DotLabel, type DotTone } from '../../components/StatusDot';
import styles from './Panel.module.css';

type PanelProps = {
  title: ReactNode;
  // Подпись с точкой над заголовком: «Другие условия», «Нужны данные»
  eyebrow?: { tone: DotTone; text: string };
  // Справа от заголовка, например название продукта
  aside?: ReactNode;
  children: ReactNode;
};

// Блок «Что делать» на странице заявки: белая карточка со скруглением 24
export function Panel({ title, eyebrow, aside, children }: PanelProps) {
  return (
    <section className={styles.panel}>
      <div className={styles.heading}>
        {eyebrow && <DotLabel tone={eyebrow.tone}>{eyebrow.text}</DotLabel>}
        <div className={styles.titleRow}>
          <Typography.TitleResponsive tag='h2' view={eyebrow ? 'medium' : 'small'} font='system'>{title}</Typography.TitleResponsive>
          {aside && <Typography.Text view='primary-small' color='secondary'>{aside}</Typography.Text>}
        </div>
      </div>
      {children}
    </section>
  );
}

type FactRowsProps = {
  rows: { label: ReactNode; value: ReactNode }[];
};

// Строки «Ставка — 19,9%» с тонкими разделителями
export function FactRows({ rows }: FactRowsProps) {
  return (
    <dl className={styles.rows}>
      {rows.map((row, index) => (
        <div key={index} className={styles.row}>
          <dt><Typography.Text view='primary-small' color='secondary'>{row.label}</Typography.Text></dt>
          <dd><Typography.Text view='primary-medium' weight='medium'>{row.value}</Typography.Text></dd>
        </div>
      ))}
    </dl>
  );
}

// Рамка с пояснением: «Для подписи понадобится код из СМС…»
export function Note({ children }: { children: ReactNode }) {
  return (
    <div className={styles.note}>
      <Typography.Text view='primary-small' tag='p' defaultMargins={false}>{children}</Typography.Text>
    </div>
  );
}
