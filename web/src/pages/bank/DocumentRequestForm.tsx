import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { BankApplication } from '../../api/types';
import styles from './Bank.module.css';

type Ask = { title: string; reason: string };

type DocumentRequestFormProps = {
  application: BankApplication;
  onChange: (application: BankApplication) => void;
};

const MAX_DOCUMENTS = 10;

// Запрос документов (S4.4): для каждого — что нужно и зачем (J9), клиент видит это пояснение
export function DocumentRequestForm({ application, onChange }: DocumentRequestFormProps) {
  const [asks, setAsks] = useState<Ask[]>([{ title: '', reason: '' }]);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (index: number, patch: Partial<Ask>) =>
    setAsks(asks.map((ask, i) => (i === index ? { ...ask, ...patch } : ask)));
  const incomplete = asks.some((ask) => !ask.title.trim() || !ask.reason.trim());

  async function submit() {
    setBusy(true);
    setError(null);
    const body = {
      items: asks.map((ask) => ({ title: ask.title.trim(), reason: ask.reason.trim() })),
      comment: comment.trim() || null,
    };
    try {
      onChange(await api<BankApplication>(`/bank/applications/${application.id}/document-request`, { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {asks.map((ask, index) => (
        <div key={index} className={styles.ask}>
          <Input
            label='Документ'
            block={true}
            placeholder='Например: договор с заказчиком'
            maxLength={200}
            value={ask.title}
            onChange={(_, { value }) => update(index, { title: value })}
          />
          <Input
            label='Зачем он нужен — увидит клиент'
            block={true}
            placeholder='Например: подтвердить выручку, на которую рассчитан кредит'
            maxLength={500}
            value={ask.reason}
            onChange={(_, { value }) => update(index, { reason: value })}
          />
          {asks.length > 1 && (
            <Button view='transparent' size={32} onClick={() => setAsks(asks.filter((_, i) => i !== index))}>
              Убрать
            </Button>
          )}
        </div>
      ))}
      {asks.length < MAX_DOCUMENTS && (
        <Button view='transparent' size={32} onClick={() => setAsks([...asks, { title: '', reason: '' }])}>
          + Ещё документ
        </Button>
      )}
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
      <Button view='secondary' size={40} loading={busy} disabled={incomplete} onClick={submit}>
        Запросить документы
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
