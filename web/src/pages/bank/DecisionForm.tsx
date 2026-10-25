import { useEffect, useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { BankApplication, DecisionIn, OfferCheck } from '../../api/types';
import { formatMonths, formatRub } from '../../format';
import { OfferHints } from './OfferHints';
import styles from './Bank.module.css';

type Result = DecisionIn['result'];

const RESULTS: { value: Result; title: string }[] = [
  { value: 'APPROVE', title: 'Одобрить' },
  { value: 'COUNTER_OFFER', title: 'Другие условия' },
  { value: 'REJECT', title: 'Отказать' },
];

type DecisionFormProps = {
  application: BankApplication;
  canReject: boolean;
  onChange: (application: BankApplication) => void;
};

// Решение сотрудника банка (S5.3, S5.4). Условия по умолчанию — из рекомендации скоринга.
export function DecisionForm({ application, canReject, onChange }: DecisionFormProps) {
  const recommendation = application.scoring;
  const recommended = recommendation?.offers?.[0];
  const [result, setResult] = useState<Result>(
    recommendation?.result === 'COUNTER_OFFER' ? 'COUNTER_OFFER' : 'APPROVE',
  );
  const [amount, setAmount] = useState<number | null>(recommended?.amount ?? application.amount);
  const [term, setTerm] = useState(String(recommended?.term_months ?? application.term_months ?? ''));
  const [rate, setRate] = useState(recommended ? String(recommended.rate) : '');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Проверка условий в скоринге с задержкой после ввода (S5.4): ключ — условия, на которые пришёл ответ
  const numericRate = rate ? Number(rate.replace(',', '.')) : null;
  const termMonths = Number(term) || null;
  const checkKey = result !== 'REJECT' && amount && termMonths ? `${amount}:${termMonths}:${numericRate ?? ''}` : null;
  const [check, setCheck] = useState<{ key: string; value: OfferCheck } | null>(null);
  useEffect(() => {
    if (!checkKey || !amount || !termMonths) return;
    const body = { amount, term_months: termMonths, rate: numericRate };
    const timer = setTimeout(() => {
      api<OfferCheck>(`/bank/applications/${application.id}/offer-check`, { method: 'POST', body })
        .then((value) => setCheck({ key: checkKey, value }))
        .catch(() => setCheck(null));
    }, 400);
    return () => clearTimeout(timer);
  }, [checkKey, amount, termMonths, numericRate, application.id]);
  const currentCheck = check && check.key === checkKey ? check.value : null;
  const outsidePolicy = result !== 'REJECT' && currentCheck !== null && !currentCheck.allowed;

  // Менеджер не может выдать условия вне политики; андеррайтер может, но только с обоснованием
  const blockedForManager = outsidePolicy && !canReject;
  const needsReason = (result === 'REJECT' || (outsidePolicy && canReject)) && !comment.trim();

  async function submit() {
    setBusy(true);
    setError(null);
    const body: DecisionIn = { result, comment: comment.trim() || null };
    if (result !== 'REJECT') {
      body.amount = amount;
      body.term_months = termMonths;
      body.rate = numericRate;
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
      {recommended && (
        <>
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            Скоринг рекомендует:{' '}
            {recommendation?.result === 'COUNTER_OFFER' ? 'другие условия' : 'одобрить'} — {formatRub(recommended.amount)} на{' '}
            {formatMonths(recommended.term_months)} под {recommended.rate}%. Условия подставлены, их можно изменить.
          </Typography.Text>
          <Gap size={12} />
        </>
      )}
      <div className={styles.choice}>
        {RESULTS.filter((option) => canReject || option.value !== 'REJECT').map((option) => (
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
          {currentCheck && (
            <OfferHints
              check={currentCheck}
              onApplySuggestion={(terms) => {
                setAmount(terms.amount);
                setTerm(String(terms.term_months));
                setRate(terms.rate === null ? '' : String(terms.rate));
              }}
            />
          )}
        </>
      )}
      <Textarea
        label={
          result === 'REJECT'
            ? 'Причина отказа — её увидит клиент'
            : outsidePolicy && canReject
              ? 'Обоснуйте отступление от кредитной политики'
              : 'Комментарий'
        }
        block={true}
        minRows={2}
        maxLength={1000}
        value={comment}
        onChange={(_, { value }) => setComment(value)}
      />
      <Gap size={16} />
      {blockedForManager && (
        <>
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            Измените условия или передайте заявку андеррайтеру.
          </Typography.Text>
          <Gap size={8} />
        </>
      )}
      <Button view='accent' size={48} loading={busy} disabled={needsReason || blockedForManager} onClick={submit}>
        {result === 'APPROVE' ? 'Подтвердить одобрение' : result === 'COUNTER_OFFER' ? 'Предложить условия' : 'Отказать'}
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
