import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, Product } from '../../api/types';
import { CompanyStep } from './CompanyStep';
import { LoanFields } from './LoanFields';
import { type LoanTerms, termsError } from './loanTerms';

type NeedInfoFormProps = {
  application: Application;
  product: Product | undefined;
  onChange: (application: Application) => void;
};

const LOAN_FIELDS = new Set(['amount', 'term_months', 'purpose']);

// Банк просит дополнить заявку (NEED_INFO): что именно — в need_info.items
export function NeedInfoForm({ application, product, onChange }: NeedInfoFormProps) {
  const needInfo = application.need_info;
  const items = needInfo?.items ?? [];
  const asksCompany = items.some((item) => item.field === 'company');
  const asksLoan = items.some((item) => LOAN_FIELDS.has(item.field));
  const questions = items.filter((item) => item.field !== 'company' && !LOAN_FIELDS.has(item.field));

  const [terms, setTerms] = useState<LoanTerms>({
    amount: application.amount,
    term: application.term_months ? String(application.term_months) : '',
    purpose: application.purpose ?? '',
  });
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const errors = termsError(product, terms);
  const missingAnswer = questions.some((item) => !answers[item.field]?.trim());
  const missingCompany = asksCompany && !application.form.company;
  const disabled = missingAnswer || missingCompany || Boolean(errors.amount || errors.term);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const body = {
        amount: terms.amount ?? undefined,
        term_months: Number(terms.term) || undefined,
        purpose: terms.purpose.trim() || undefined,
        extra: answers,
        comment: comment.trim() || undefined,
      };
      onChange(await api<Application>(`/applications/${application.id}/info`, { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Plate view='attention' rounded={true} border={true} title='Банку нужны дополнительные данные'>
      <ul>
        {items.map((item) => (
          <li key={item.field}>
            <Typography.Text view='primary-medium'>{item.message}</Typography.Text>
          </li>
        ))}
      </ul>
      {needInfo?.comment && (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Комментарий банка: {needInfo.comment}
        </Typography.Text>
      )}

      {asksCompany && (
        <>
          <Gap size={16} />
          <CompanyStep application={application} onChange={onChange} />
        </>
      )}
      {asksLoan && (
        <>
          <Gap size={16} />
          <LoanFields product={product} terms={terms} onChange={setTerms} />
        </>
      )}
      {questions.map((item) => (
        <div key={item.field}>
          <Gap size={16} />
          <Textarea
            label={item.message}
            block={true}
            minRows={2}
            maxLength={1000}
            value={answers[item.field] ?? ''}
            onChange={(_, { value }) => setAnswers({ ...answers, [item.field]: value })}
          />
        </div>
      ))}
      <Gap size={16} />
      <Textarea
        label='Комментарий для банка (необязательно)'
        block={true}
        minRows={2}
        maxLength={1000}
        value={comment}
        onChange={(_, { value }) => setComment(value)}
      />
      <Gap size={16} />
      <Button view='accent' size={48} loading={busy} disabled={disabled} onClick={submit}>
        Отправить данные
      </Button>
      {error && (
        <>
          <Gap size={8} />
          <Typography.Text view='primary-small' color='negative'>
            {error}
          </Typography.Text>
        </>
      )}
    </Plate>
  );
}
