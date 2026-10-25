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

type ClientRequestFormProps = {
  application: BankApplication;
  onChange: (application: BankApplication) => void;
};

const MAX_ITEMS = 10;

// Один запрос клиенту (S4.4): вопросы и документы с пояснением, зачем каждый (J9) — клиент отвечает в своём кабинете
export function ClientRequestForm({ application, onChange }: ClientRequestFormProps) {
  const [questions, setQuestions] = useState<string[]>(['']);
  const [asks, setAsks] = useState<Ask[]>([]);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filledQuestions = questions.map((q) => q.trim()).filter(Boolean);
  const incompleteAsk = asks.some((ask) => !ask.title.trim() || !ask.reason.trim());
  const empty = filledQuestions.length === 0 && asks.length === 0;
  const updateAsk = (index: number, patch: Partial<Ask>) =>
    setAsks(asks.map((ask, i) => (i === index ? { ...ask, ...patch } : ask)));

  async function submit() {
    setBusy(true);
    setError(null);
    const stamp = Date.now();
    const body = {
      items: filledQuestions.map((message, i) => ({ field: `request_${stamp}_${i}`, message })),
      documents: asks.map((ask) => ({ title: ask.title.trim(), reason: ask.reason.trim() })),
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
      <Typography.Text view='primary-small' weight='bold' tag='p' defaultMargins={false}>
        Вопросы
      </Typography.Text>
      <Gap size={8} />
      {questions.map((question, index) => (
        <div key={`q${index}`} className={styles.question}>
          <Input
            label='Что нужно от клиента'
            block={true}
            placeholder='Например: поясните просрочку по кредиту в 2025 году'
            maxLength={500}
            value={question}
            onChange={(_, { value }) => setQuestions(questions.map((q, i) => (i === index ? value : q)))}
          />
          {questions.length > 1 && (
            <Button view='transparent' size={32} onClick={() => setQuestions(questions.filter((_, i) => i !== index))}>
              Убрать
            </Button>
          )}
        </div>
      ))}
      {questions.length < MAX_ITEMS && (
        <Button view='transparent' size={32} onClick={() => setQuestions([...questions, ''])}>
          + Ещё вопрос
        </Button>
      )}
      <Gap size={16} />
      <Typography.Text view='primary-small' weight='bold' tag='p' defaultMargins={false}>
        Документы
      </Typography.Text>
      <Gap size={8} />
      {asks.map((ask, index) => (
        <div key={`d${index}`} className={styles.ask}>
          <Input
            label='Документ'
            block={true}
            placeholder='Например: договор с заказчиком'
            maxLength={200}
            value={ask.title}
            onChange={(_, { value }) => updateAsk(index, { title: value })}
          />
          <Input
            label='Зачем он нужен — увидит клиент'
            block={true}
            placeholder='Например: подтвердить выручку, на которую рассчитан кредит'
            maxLength={500}
            value={ask.reason}
            onChange={(_, { value }) => updateAsk(index, { reason: value })}
          />
          <Button view='transparent' size={32} onClick={() => setAsks(asks.filter((_, i) => i !== index))}>
            Убрать
          </Button>
        </div>
      ))}
      {asks.length < MAX_ITEMS && (
        <Button view='transparent' size={32} onClick={() => setAsks([...asks, { title: '', reason: '' }])}>
          + Документ
        </Button>
      )}
      <Gap size={16} />
      <Textarea
        label='Комментарий (необязательно)'
        block={true}
        minRows={2}
        maxLength={1000}
        value={comment}
        onChange={(_, { value }) => setComment(value)}
      />
      <Gap size={12} />
      <Button view='secondary' size={40} loading={busy} disabled={empty || incompleteAsk} onClick={submit}>
        Отправить запрос клиенту
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
