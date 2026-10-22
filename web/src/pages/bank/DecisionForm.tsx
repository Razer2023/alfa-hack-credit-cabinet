import { useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { BankApplication, DecisionIn } from '../../api/types';
import styles from './Bank.module.css';

type Result = DecisionIn['result'];

const RESULTS: { value: Result; title: string }[] = [
  { value: 'APPROVE', title: 'Одобрить' },
  { value: 'COUNTER_OFFER', title: 'Другие условия' },
  { value: 'REJECT', title: 'Отказать' },
];

type DecisionFormProps = {
  application: BankApplication;
  onChange: (application: BankApplication) => void;
};

// Решение андеррайтера по заявке на ручном рассмотрении (S5.3, S5.4)
export function DecisionForm({ application, onChange }: DecisionFormProps) {
  const [result, setResult] = useState<Result>('APPROVE');
  const [amount, setAmount] = useState<number | null>(application.amount);
  const [term, setTerm] = useState(application.term_months ? String(application.term_months) : '');
  const [rate, setRate] = useState('');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsReason = result === 'REJECT' && !comment.trim();

  async function submit() {
    setBusy(true);
    setError(null);
    const body: DecisionIn = { result, comment: comment.trim() || null };
    if (result !== 'REJECT') {
      body.amount = amount;
      body.term_months = Number(term) || null;
      body.rate = rate ? Number(rate.replace(',', '.')) : null;
    }
    try {
      onChange(await api<BankApplication>(`/bank/applications/${application.id}/decision`, { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className={styles.choice}>
        {RESULTS.map((option) => (
          <Button
            key={option.value}
            view={result === option.value ? 'primary' : 'secondary'}
            size={40}
            onClick={() => setResult(option.value)}
          >
            {option.title}
          </Button>
        ))}
      </div>
      <Gap size={16} />
      {result !== 'REJECT' && (
        <>
          <div className={styles.fields}>
            <AmountInput
              label='Сумма'
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
              onChange={(_, { value }) => setTerm(value.replace(/\D/g, ''))}
            />
            <Input
              label='Ставка, %'
              block={true}
              inputMode='decimal'
              hint='Пусто — базовая ставка продукта'
              value={rate}
              onChange={(_, { value }) => setRate(value.replace(/[^\d.,]/g, ''))}
            />
          </div>
          <Gap size={12} />
        </>
      )}
      <Textarea
        label={result === 'REJECT' ? 'Причина отказа — её увидит клиент' : 'Комментарий'}
        block={true}
        minRows={2}
        maxLength={1000}
        value={comment}
        onChange={(_, { value }) => setComment(value)}
      />
      <Gap size={16} />
      <Button view='accent' size={48} loading={busy} disabled={needsReason} onClick={submit}>
        Принять решение
      </Button>
      {error && (
        <>
          <Gap size={8} />
          <Typography.Text view='primary-small' color='negative'>
            {error}
          </Typography.Text>
        </>
      )}
    </>
  );
}
