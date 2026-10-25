import { useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Status } from '@alfalab/core-components/status';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Precheck, Product } from '../../api/types';
import { formatMonths, formatRub } from '../../format';
import styles from './ProductCard.module.css';

const CHANCE = {
  HIGH: { color: 'green', label: 'Высокие шансы' },
  MEDIUM: { color: 'orange', label: 'Средние шансы' },
  LOW: { color: 'red', label: 'Низкие шансы' },
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
      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
        Оценим по ИНН вашей компании: ЕГРЮЛ, ФНС, кредитная история и обороты. Это не заявка.
      </Typography.Text>
      <Gap size={12} />
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
      <Gap size={12} />
      <Button view='secondary' size={40} block={true} loading={busy} onClick={estimate}>
        Оценить
      </Button>
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
      {result && (
        <div className={styles.precheckResult} aria-live='polite'>
          <Status view='soft' color={CHANCE[result.chance].color}>
            {CHANCE[result.chance].label}
          </Status>
          <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
            {result.title}
          </Typography.Text>
          <Typography.Text view='primary-small' tag='p' defaultMargins={false}>
            {result.explanation}
          </Typography.Text>
          {result.max_amount && (
            <Typography.Text view='primary-small' tag='p' defaultMargins={false}>
              Можно получить до <b>{formatRub(result.max_amount)}</b>
              {result.max_amount_term_months && ` на ${formatMonths(result.max_amount_term_months)}`}
            </Typography.Text>
          )}
          {result.terms && (
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              Ориентировочно: {formatRub(result.terms.amount)} на {formatMonths(result.terms.term_months)} под{' '}
              {result.terms.rate}%, платёж {formatRub(result.terms.monthly_payment)} в месяц
            </Typography.Text>
          )}
          {(result.reasons ?? []).map((reason) => (
            <Typography.Text key={reason} view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              • {reason}
            </Typography.Text>
          ))}
          <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
            Предварительная оценка, не решение банка. Не влияет на кредитную историю.
          </Typography.Text>
        </div>
      )}
    </div>
  );
}
