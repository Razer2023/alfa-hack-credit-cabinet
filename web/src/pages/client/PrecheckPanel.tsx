import { useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Button } from '@alfalab/core-components/button';
import { Input } from '@alfalab/core-components/input';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Precheck, Product } from '../../api/types';
import { formatMonths, formatRub } from '../../format';
import { DotLabel } from '../../components/StatusDot';
import { Term } from '../../components/Term';
import styles from './Catalog.module.css';

const CHANCE = {
  HIGH: { tone: 'positive', label: 'Высокие шансы' },
  MEDIUM: { tone: 'attention', label: 'Средние шансы' },
  LOW: { tone: 'negative', label: 'Низкие шансы' },
} as const;

type PrecheckPanelProps = {
  product: Product;
};

// Предоценка суммы и шансов по ИНН до заявки (S2.1): ничего не сохраняется
export function PrecheckPanel({ product }: PrecheckPanelProps) {
  const [amount, setAmount] = useState<number | null>(null);
  const [term, setTerm] = useState('');
  const [result, setResult] = useState<Precheck | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function estimate() {
    setBusy(true);
    setError(null);
    const body = { product_code: product.code, amount: amount ?? undefined, term_months: Number(term) || undefined };
    try {
      setResult(await api<Precheck>('/precheck', { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.precheck}>
      <div className={styles.precheckFields}>
        <AmountInput
          label='Сумма (необязательно)'
          block={true}
          currency='RUB'
          integersOnly={true}
          positiveOnly={true}
          value={amount === null ? null : amount * 100}
          onChange={(_, { value }) => setAmount(value === null ? null : Math.round(value / 100))}
        />
        <Input
          label='Срок, мес.'
          block={true}
          inputMode='numeric'
          value={term}
          hint={`${product.min_term_months}–${product.max_term_months}`}
          onChange={(_, { value }) => setTerm(value.replace(/\D/g, ''))}
        />
      </div>
      <div className={styles.note}>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Это не заявка, на кредитную историю не влияет. Смотрим <Term>ЕГРЮЛ</Term>, <Term>ФНС</Term>,{' '}
          <Term>кредитная история</Term> и обороты.
        </Typography.Text>
      </div>
      <Button view='secondary' size={48} block={true} loading={busy} onClick={estimate}>
        Оценить
      </Button>
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
      {result && (
        <div className={styles.precheckResult} aria-live='polite'>
          <DotLabel tone={CHANCE[result.chance].tone}>{CHANCE[result.chance].label}</DotLabel>
          <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
            {result.title}
          </Typography.Text>
          <Typography.Text view='primary-small' tag='p' defaultMargins={false}>
            {result.explanation}
          </Typography.Text>
          {result.max_amount && (
            <>
              <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                Можно получить до
              </Typography.Text>
              <Typography.Title className={styles.number} tag='div' view='medium' font='system'>
                {formatRub(result.max_amount)}
              </Typography.Title>
              {result.max_amount_term_months && (
                <Typography.Text view='primary-small' tag='p' defaultMargins={false}>
                  на {formatMonths(result.max_amount_term_months)}
                </Typography.Text>
              )}
            </>
          )}
          {result.terms && (
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              Ориентировочно: {formatRub(result.terms.amount)} на {formatMonths(result.terms.term_months)} под{' '}
              {result.terms.rate}%, платёж {formatRub(result.terms.monthly_payment)} в месяц
            </Typography.Text>
          )}
          {(result.reasons ?? []).length > 0 && (
            <ul className={styles.reasons}>
              {(result.reasons ?? []).map((reason) => (
                <li key={reason}>
                  <Typography.Text view='primary-small'>{reason}</Typography.Text>
                </li>
              ))}
            </ul>
          )}
          <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
            Предварительная оценка, не решение банка.
          </Typography.Text>
        </div>
      )}
    </div>
  );
}
