import { useEffect, useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Input } from '@alfalab/core-components/input';
import { Tag } from '@alfalab/core-components/tag';
import { Typography } from '@alfalab/core-components/typography';

import { api } from '../../api/client';
import type { ProductMatch } from '../../api/types';
import styles from './ProductMatcher.module.css';

export type MatchRequest = { purpose: string; amount: number | null; term_months: number | null };

type ProductMatcherProps = {
  // Подбор, на который пришёл ответ: null — цель не выбрана, каталог в исходном порядке
  onResult: (result: { request: MatchRequest; matches: ProductMatch[] } | null) => void;
};

// Подбор продукта по цели (S1.2): правила каталога — цель, сумма и срок в рамках продукта, затем ставка
export function ProductMatcher({ onResult }: ProductMatcherProps) {
  const [purposes, setPurposes] = useState<string[]>([]);
  const [purpose, setPurpose] = useState<string | null>(null);
  const [amount, setAmount] = useState<number | null>(null);
  const [term, setTerm] = useState('');

  useEffect(() => {
    api<string[]>('/products/purposes').then(setPurposes).catch(() => setPurposes([]));
  }, []);

  const termMonths = Number(term) || null;
  useEffect(() => {
    if (!purpose) {
      onResult(null);
      return;
    }
    const request = { purpose, amount, term_months: termMonths };
    const timer = setTimeout(() => {
      api<ProductMatch[]>('/products/match', { method: 'POST', body: request })
        .then((matches) => onResult({ request, matches }))
        .catch(() => onResult(null));
    }, 300);
    return () => clearTimeout(timer);
  }, [purpose, amount, termMonths, onResult]);

  if (purposes.length === 0) return null;

  return (
    <section className={styles.matcher} aria-label='Подбор кредита по цели'>
      <Typography.Title tag='h2' view='xsmall' font='system'>
        На что нужны деньги?
      </Typography.Title>
      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
        Выберите задачу — покажем, какой кредит подходит и почему.
      </Typography.Text>
      <div className={styles.tags}>
        {purposes.map((item) => (
          <Tag
            key={item}
            size={40}
            shape='rounded'
            checked={purpose === item}
            onClick={() => setPurpose(purpose === item ? null : item)}
          >
            {item}
          </Tag>
        ))}
      </div>
      {purpose && (
        <div className={styles.fields}>
          <AmountInput
            label='Сколько нужно'
            block={true}
            currency='RUB'
            integersOnly={true}
            positiveOnly={true}
            value={amount === null ? null : amount * 100}
            hint='Необязательно'
            onChange={(_, { value }) => setAmount(value === null ? null : Math.round(value / 100))}
          />
          <Input
            label='На сколько месяцев'
            block={true}
            inputMode='numeric'
            value={term}
            hint='Необязательно'
            onChange={(_, { value }) => setTerm(value.replace(/\D/g, '').slice(0, 3))}
          />
        </div>
      )}
    </section>
  );
}
