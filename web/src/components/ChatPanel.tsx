import { useEffect, useRef, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Plate } from '@alfalab/core-components/plate';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../api/client';
import type { ChatMessage } from '../api/types';
import { useUser } from '../auth/AuthContext';
import { useApplicationEvents } from '../events';
import { formatDateTime } from '../format';
import styles from './ChatPanel.module.css';

type ChatPanelProps = {
  applicationId: string;
  // Клиент пишет в /applications, сотрудник — в /bank/applications
  basePath: '/applications' | '/bank/applications';
  title: string;
};

// Переписка по заявке внутри кабинета (S4.10): новые сообщения приходят по общему SSE-потоку
export function ChatPanel({ applicationId, basePath, title }: ChatPanelProps) {
  const user = useUser();
  const isClient = user.role === 'CLIENT';
  const path = `${basePath}/${applicationId}/messages`;
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const thread = useRef<HTMLDivElement>(null);

  function load() {
    api<ChatMessage[]>(path)
      .then(setMessages)
      .catch((e) => setError(errorMessage(e)));
  }

  useEffect(load, [path]);

  useApplicationEvents((event) => {
    if (event.application_id === applicationId && event.type === 'MESSAGE') load();
  });

  useEffect(() => {
    thread.current?.scrollTo({ top: thread.current.scrollHeight });
  }, [messages.length]);

  async function send() {
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const message = await api<ChatMessage>(path, {
        method: 'POST',
        body: { text },
      });
      setMessages((current) => (current.some((m) => m.id === message.id) ? current : [...current, message]));
      setText('');
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Plate view='common' rounded={true} border={true} title={title}>
      {messages.length === 0 ? (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          {isClient ? 'Задайте вопрос по заявке — менеджер ответит здесь же.' : 'Клиент пока ничего не писал.'}
        </Typography.Text>
      ) : (
        <div ref={thread} className={styles.thread} aria-live='polite'>
          {messages.map((message) => {
            const own = (message.author_role === 'CLIENT') === isClient;
            return (
              <div key={message.id} className={own ? `${styles.message} ${styles.own}` : styles.message}>
                <Typography.Text
                  view='primary-small'
                  color={own ? 'secondary-inverted' : 'secondary'}
                  tag='p'
                  defaultMargins={false}
                >
                  {own ? 'Вы' : message.author_name} · {formatDateTime(message.created_at)}
                </Typography.Text>
                <Typography.Text
                  view='primary-small'
                  color={own ? 'primary-inverted' : 'primary'}
                  tag='p'
                  defaultMargins={false}
                >
                  {message.text}
                </Typography.Text>
              </div>
            );
          })}
        </div>
      )}
      <Textarea
        label='Сообщение'
        block={true}
        minRows={2}
        maxLength={2000}
        value={text}
        onChange={(_, { value }) => setText(value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) send();
        }}
      />
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
      <Button view='secondary' size={40} loading={busy} disabled={!text.trim()} onClick={send}>
        Отправить
      </Button>
    </Plate>
  );
}
