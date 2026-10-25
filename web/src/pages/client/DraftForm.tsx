import { useEffect, useState } from 'react';
import { Gap } from '@alfalab/core-components/gap';
import { Typography } from '@alfalab/core-components/typography';

import { Card } from '../../components/Card';
import { api } from '../../api/client';
import type { Application, CodeRequest, Product } from '../../api/types';
import { CodeConfirm } from '../../components/CodeConfirm';
import { Term } from '../../components/Term';
import { CompanyStep } from './CompanyStep';
import { LoanFields } from './LoanFields';
import { type LoanTerms, termsReady } from './loanTerms';

type DraftFormProps = {
  application: Application;
  product: Product | undefined;
  onChange: (application: Application) => void;
};

type SaveState = 'idle' | 'saving' | 'saved' | 'error';

function patchBody(terms: LoanTerms) {
  return {
    amount: terms.amount ?? undefined,
    term_months: Number(terms.term) || undefined,
    purpose: terms.purpose.trim() || undefined,
  };
}

function isDirty(terms: LoanTerms, application: Application): boolean {
  const body = patchBody(terms);
  return (
    (body.amount ?? null) !== application.amount ||
    (body.term_months ?? null) !== application.term_months ||
    (body.purpose ?? null) !== application.purpose
  );
}

// Мастер заявки (S3.1–S3.4): компания по ИНН → условия → отправка с кодом
export function DraftForm({ application, product, onChange }: DraftFormProps) {
  const [terms, setTerms] = useState<LoanTerms>({
    amount: application.amount,
    term: application.term_months ? String(application.term_months) : '',
    purpose: application.purpose ?? '',
  });
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const dirty = isDirty(terms, application);

  // Автосохранение черновика: изменения не теряются при перезагрузке (S3.4)
  useEffect(() => {
    if (!isDirty(terms, application)) return;
    const timer = setTimeout(() => {
      setSaveState('saving');
      api<Application>(`/applications/${application.id}`, { method: 'PATCH', body: patchBody(terms) })
        .then((updated) => {
          onChange(updated);
          setSaveState('saved');
        })
        .catch(() => setSaveState('error'));
    }, 600);
    return () => clearTimeout(timer);
  }, [terms, application, onChange]);

  async function requestCode() {
    if (dirty) {
      const body = patchBody(terms);
      onChange(await api<Application>(`/applications/${application.id}`, { method: 'PATCH', body }));
    }
    return api<CodeRequest>(`/applications/${application.id}/submit/code`, { method: 'POST' });
  }

  async function confirm(confirmationId: string, code: string) {
    const body = { confirmation_id: confirmationId, code };
    onChange(await api<Application>(`/applications/${application.id}/submit/confirm`, { method: 'POST', body }));
  }

  const ready = termsReady(product, terms);

  return (
    <>
      <Card title='1. Компания'>
        <CompanyStep application={application} onChange={onChange} />
      </Card>
      <Gap size={16} />
      <Card title='2. Условия кредита'>
        <LoanFields product={product} terms={terms} onChange={setTerms} />
        <Gap size={8} />
        <Typography.Text view='primary-small' color={saveState === 'error' ? 'negative' : 'secondary'}>
          {saveState === 'saving' && 'Сохраняем черновик…'}
          {saveState === 'saved' && !dirty && 'Черновик сохранён'}
          {saveState === 'error' && 'Не удалось сохранить черновик, проверьте соединение'}
        </Typography.Text>
      </Card>
      <Gap size={16} />
      <Card title='3. Отправка в банк'>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          {ready ? (
            <>
              Подтвердите отправку кодом — это ваша <Term>простая электронная подпись</Term>.
            </>
          ) : (
            'Заполните сумму, срок и цель кредита.'
          )}
        </Typography.Text>
        <Gap size={12} />
        <CodeConfirm buttonText='Отправить заявку' disabled={!ready} requestCode={requestCode} confirm={confirm} />
      </Card>
    </>
  );
}
