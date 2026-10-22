import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { BankApplication } from '../../api/types';

type InfoRequestFormProps = {
  application: BankApplication;
  onChange: (application: BankApplication) => void;
};

// Запрос данных у клиента (S4.4): клиент увидит вопрос и ответит в своём кабинете
export function InfoRequestForm({ application, onChange }: InfoRequestFormProps) {
  const [question, setQuestion] = useState('');
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true);
    setError(null);
    const body = {
      items: [{ field: `request_${Date.now()}`, message: question.trim() }],
      comment: comment.trim() || null,
    };
    try {
      onChange(await api<BankApplication>(`/bank/applications/${application.id}/info-request`, { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Input
        label='Что нужно от клиента'
        block={true}
        placeholder='Например: поясните просрочку по кредиту в 2025 году'
        value={question}
        onChange={(_, { value }) => setQuestion(value)}
      />
      <Gap size={12} />
      <Textarea
        label='Комментарий (необязательно)'
        block={true}
        minRows={2}
        maxLength={1000}
        value={comment}
        onChange={(_, { value }) => setComment(value)}
      />
      <Gap size={12} />
      <Button view='secondary' size={40} loading={busy} disabled={!question.trim()} onClick={submit}>
        Запросить данные
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
