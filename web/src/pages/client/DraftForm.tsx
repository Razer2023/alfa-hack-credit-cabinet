import { useEffect, useState } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import { api } from '../../api/client';
import type { Application, CodeRequest, Product } from '../../api/types';
import { CodeConfirm } from '../../components/CodeConfirm';
import { Money } from '../../components/Money';
import { Term } from '../../components/Term';
import { formatTime } from '../../format';
import { CompanyStep } from './CompanyStep';
import styles from './DraftForm.module.css';
import { LoanFields } from './LoanFields';
import { type LoanTerms, termsReady } from './loanTerms';
import { usePayment } from './usePayment';

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

// Сроки этапов после отправки — те же, что в «Как получить кредит»
const NEXT_STEPS = [
  { title: 'Проверка данных', time: '1–2 мин' },
  { title: 'Оценка заявки', time: '1–2 мин' },
  { title: 'Подтверждение сотрудником', time: 'до 2 часов' },
];

// Мастер заявки (S3.1–S3.4): «Заявка на кредит для бизнеса» — компания по ИНН, сумма и срок, цель, отправка с кодом
export function DraftForm({ application, product, onChange }: DraftFormProps) {
  const [terms, setTerms] = useState<LoanTerms>({
    amount: application.amount,
    term: application.term_months ? String(application.term_months) : '',
    purpose: application.purpose ?? '',
  });
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const dirty = isDirty(terms, application);
  const payment = usePayment(product, terms);

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
  const saveText = saveState === 'saving' ? 'Сохраняем черновик…'
    : saveState === 'error' ? 'Не удалось сохранить черновик, проверьте соединение'
    : dirty ? '' : `Черновик сохранён в ${formatTime(application.updated_at)}`;

  return (
    <div className={styles.layout}>
      <section className={styles.form} aria-labelledby='draft-title'>
        <div className={styles.heading}>
          <Typography.TitleResponsive id='draft-title' tag='h2' view='medium' font='system'>
            Заявка на кредит для бизнеса
          </Typography.TitleResponsive>
          <Typography.Text view='secondary-large' color={saveState === 'error' ? 'negative' : 'secondary'} aria-live='polite'>
            {saveText}
          </Typography.Text>
        </div>

        <div className={styles.group}>
          <Typography.Title tag='h3' view='xsmall' font='system'>Компания</Typography.Title>
          <CompanyStep application={application} onChange={onChange} />
        </div>

        <LoanFields product={product} terms={terms} onChange={setTerms} grouped={true} />

        <div className={styles.submit}>
          <div className={styles.note}>
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              {ready ? (
                <>Данные защищены. Отправка — по коду из СМС, это ваша <Term>простая электронная подпись</Term></>
              ) : (
                'Заполните сумму, срок и цель кредита — после этого заявку можно отправить.'
              )}
            </Typography.Text>
          </div>
          <div className={styles.confirm}>
            <CodeConfirm buttonText='Отправить заявку' disabled={!ready} requestCode={requestCode} confirm={confirm} />
          </div>
        </div>
      </section>

      <aside className={styles.aside}>
        <div className={styles.card}>
          <div>
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              <Term>Платёж в месяц</Term>
            </Typography.Text>
            <Typography.Title className={styles.number} tag='div' view='medium' font='system'>
              {payment ? <Money value={payment.monthly_payment} bold={true} /> : '—'}
            </Typography.Title>
          </div>
          <div className={styles.line}>
            <Typography.Text view='primary-small' color='secondary'><Term>Ставка</Term></Typography.Text>
            <Typography.Text view='primary-medium' weight='medium'>
              {payment ? `${payment.rate}%` : product ? `от ${product.base_rate}%` : '—'}
            </Typography.Text>
          </div>
          <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
            {payment ? 'По базовой ставке. Точные условия — в решении банка.' : 'Укажите сумму и срок — посчитаем платёж.'}
          </Typography.Text>
        </div>
        <div className={styles.card}>
          <Typography.Text view='primary-large' weight='bold' tag='p' defaultMargins={false}>Что будет дальше</Typography.Text>
          <ul className={styles.steps}>
            {NEXT_STEPS.map((step) => (
              <li key={step.title} className={styles.line}>
                <Typography.Text view='primary-small'>{step.title}</Typography.Text>
                <Typography.Text view='primary-small' color='secondary'>{step.time}</Typography.Text>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </div>
  );
}
