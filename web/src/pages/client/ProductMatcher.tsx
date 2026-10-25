import { useEffect, useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Input } from '@alfalab/core-components/input';
import { Tag } from '@alfalab/core-components/tag';
import { Typography } from '@alfalab/core-components/typography';

import { api } from '../../api/client';
import type { ProductMatch, Purposes } from '../../api/types';
import styles from './ProductMatcher.module.css';

// purpose — цель каталога для подбора, title — формулировка для бизнеса клиента, она же попадает в заявку
export type MatchRequest = { purpose: string; title: string; amount: number | null; term_months: number | null };

type ProductMatcherProps = {
  // Подбор, на который пришёл ответ: null — цель не выбрана, каталог в исходном порядке
  onResult: (result: { request: MatchRequest; matches: ProductMatch[] } | null) => void;
};

// Подбор продукта по цели (S1.2): задачи — под отрасль клиента по ОКВЭД, правила каталога — цель, сумма и срок, затем ставка
export function ProductMatcher({ onResult }: ProductMatcherProps) {
  const [purposes, setPurposes] = useState<Purposes | null>(null);
  const [selected, setSelected] = useState<Purposes['items'][number] | null>(null);
  const [amount, setAmount] = useState<number | null>(null);
  const [term, setTerm] = useState('');

  useEffect(() => {
    api<Purposes>('/products/purposes').then(setPurposes).catch(() => setPurposes(null));
  }, []);

  const termMonths = Number(term) || null;
  useEffect(() => {
    if (!selected) {
      onResult(null);
      return;
    }
    const request = { purpose: selected.purpose, title: selected.title, amount, term_months: termMonths };
    const timer = setTimeout(() => {
      api<ProductMatch[]>('/products/match', { method: 'POST', body: request })
        .then((matches) => onResult({ request, matches }))
        .catch(() => onResult(null));
    }, 300);
    return () => clearTimeout(timer);
  }, [selected, amount, termMonths, onResult]);

  if (!purposes || purposes.items.length === 0) return null;

  return (
    <section className={styles.matcher} aria-label='Подбор кредита по цели'>
      <Typography.Title tag='h2' view='xsmall' font='system'>
        На что нужны деньги?
      </Typography.Title>
      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
        {purposes.business
          ? `Задачи, с которыми чаще приходят в отрасли «${purposes.business}». Выберите — покажем, какой кредит подходит и почему.`
          : 'Выберите задачу — покажем, какой кредит подходит и почему.'}
      </Typography.Text>
      <div className={styles.tags}>
        {purposes.items.map((item) => (
          <Tag
            key={item.title}
            size={40}
            shape='rounded'
            checked={selected?.title === item.title}
            onClick={() => setSelected(selected?.title === item.title ? null : item)}
          >
            {item.title}
          </Tag>
        ))}
      </div>
      {selected && (
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
