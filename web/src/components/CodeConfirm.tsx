import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { CodeInput } from '@alfalab/core-components/code-input';
import { Gap } from '@alfalab/core-components/gap';
import { Typography } from '@alfalab/core-components/typography';

import { errorMessage } from '../api/client';
import type { CodeRequest } from '../api/types';

type CodeConfirmProps = {
  buttonText: string;
  disabled?: boolean;
  requestCode: () => Promise<CodeRequest>;
  confirm: (confirmationId: string, code: string) => Promise<void>;
};

// Подтверждение кодом (мок ПЭП, S3.3 и S7.1). SMS по условиям кейса нет, поэтому код показывается на экране.
export function CodeConfirm({ buttonText, disabled = false, requestCode, confirm }: CodeConfirmProps) {
  const [request, setRequest] = useState<CodeRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Новый ключ сбрасывает поле ввода после ошибки или нового кода
  const [attempt, setAttempt] = useState(0);

  async function onRequest() {
    setBusy(true);
    setError(null);
    try {
      setRequest(await requestCode());
      setAttempt((value) => value + 1);
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  async function onComplete(code: string) {
    if (!request) return;
    setBusy(true);
    setError(null);
    try {
      await confirm(request.confirmation_id, code);
    } catch (e) {
      setError(errorMessage(e));
      setAttempt((value) => value + 1);
    } finally {
      setBusy(false);
    }
  }

  if (!request) {
    return (
      <>
        <Button view='accent' size={48} loading={busy} disabled={disabled} onClick={onRequest}>
          {buttonText}
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

  return (
    <>
      <Typography.Text view='primary-medium' tag='p' defaultMargins={false}>
        Введите код подтверждения
      </Typography.Text>
      {request.demo_code && (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Код из SMS (демо): <b>{request.demo_code}</b>
        </Typography.Text>
      )}
      <Gap size={12} />
      <CodeInput key={attempt} fields={6} disabled={busy} error={error ?? undefined} onComplete={onComplete} />
      <Gap size={12} />
      <Button view='transparent' size={32} disabled={busy} onClick={onRequest}>
        Получить новый код
      </Button>
    </>
  );
}
