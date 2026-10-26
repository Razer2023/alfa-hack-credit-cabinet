import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, CodeRequest, Offer } from '../../api/types';
import { CodeConfirm } from '../../components/CodeConfirm';
import { Term } from '../../components/Term';
import { formatMonths, formatRub } from '../../format';
import styles from './OfferBlock.module.css';
import { FactRows, Note, Panel } from './Panel';

type OfferBlockProps = {
  application: Application;
  productName: string;
  onChange: (application: Application) => void;
};

// Условия, которые подписывает клиент: принятое контрпредложение или стандартное предложение
function activeOffer(offers: Offer[]): Offer | undefined {
  return (
    offers.find((offer) => offer.status === 'ACCEPTED') ??
    offers.find((offer) => offer.status === 'PROPOSED' && offer.kind === 'STANDARD')
  );
}

// Решение и условия (S6.1), контрпредложение (S6.2), подписание (S7.1)
export function OfferBlock({ application, productName, onChange }: OfferBlockProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const path = `/applications/${application.id}`;
  const reasons = application.decision?.reasons ?? [];

  async function act(request: () => Promise<Application>) {
    setBusy(true);
    setError(null);
    try {
      onChange(await request());
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const accept = (offer: Offer) => act(() => api<Application>(`${path}/offers/${offer.id}/accept`, { method: 'POST' }));
  const decline = () => act(() => api<Application>(`${path}/cancel`, { method: 'POST', body: { reason: 'Клиент отказался от условий' } }));

  const errorText = error && (
    <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
      {error}
    </Typography.Text>
  );
  const footnote = (
    <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
      Окончательные условия — в договоре.
    </Typography.Text>
  );

  if (application.status.code === 'COUNTER_OFFER') {
    const proposed = application.offers.filter((offer) => offer.status === 'PROPOSED');
    const single = proposed.length === 1;
    return (
      <Panel title='Банк предлагает другие условия' eyebrow={{ tone: 'attention', text: 'Другие условия' }}>
        <div className={styles.intro}>
          {reasons.map((reason) => (
            <Typography.Text key={reason.code} view='primary-medium' tag='p' defaultMargins={false}>
              {reason.text}
            </Typography.Text>
          ))}
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            Это <Term name='Контрпредложение'>контрпредложение</Term>: условия можно принять или отказаться.
          </Typography.Text>
        </div>
        <div className={styles.compare}>
          <div className={`${styles.option} ${styles.requested}`}>
            <Typography.Title tag='h3' view='small' font='system' color='secondary'>Вы просили</Typography.Title>
            <Typography.TitleResponsive className={styles.amount} tag='div' view='xlarge' font='system' color='secondary'>
              {application.amount !== null ? formatRub(application.amount) : '—'}
            </Typography.TitleResponsive>
            <FactRows rows={[{ label: 'Срок', value: application.term_months !== null ? formatMonths(application.term_months) : '—' }]} />
          </div>
          {proposed.map((offer) => (
            <div key={offer.id} className={`${styles.option} ${styles.proposed}`}>
              <Typography.Title tag='h3' view='small' font='system'>Банк предлагает</Typography.Title>
              <div className={styles.was}>
                <Typography.TitleResponsive className={styles.amount} tag='div' view='xlarge' font='system'>
                  {formatRub(offer.amount)}
                </Typography.TitleResponsive>
                {application.amount !== null && application.amount !== offer.amount && (
                  <Typography.Text view='primary-small' color='secondary'>было {formatRub(application.amount)}</Typography.Text>
                )}
              </div>
              <div>
                <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}><Term>Платёж в месяц</Term></Typography.Text>
                <Typography.Title className={styles.payment} tag='div' view='medium' font='system'>{formatRub(offer.monthly_payment)}</Typography.Title>
              </div>
              <FactRows
                rows={[
                  { label: <Term>Ставка</Term>, value: `${offer.rate}%` },
                  {
                    label: 'Срок',
                    value: (
                      <>
                        {application.term_months !== null && application.term_months !== offer.term_months && (
                          <Typography.Text className={styles.before} view='primary-small' color='secondary'>
                            было {application.term_months}
                          </Typography.Text>
                        )}
                        {formatMonths(offer.term_months)}
                      </>
                    ),
                  },
                ]}
              />
              {!single && (
                <Button view='accent' size={48} loading={busy} onClick={() => accept(offer)}>Принять условия</Button>
              )}
            </div>
          ))}
        </div>
        <div className={styles.actions}>
          {single && (
            <Button view='accent' size={56} loading={busy} onClick={() => accept(proposed[0])}>Принять условия</Button>
          )}
          <Button view='secondary' size={56} disabled={busy} onClick={decline}>Отказаться</Button>
        </div>
        {errorText}
        {footnote}
      </Panel>
    );
  }

  const offer = activeOffer(application.offers);
  if (!offer) return null;

  async function requestCode() {
    return api<CodeRequest>(`${path}/sign/code`, { method: 'POST' });
  }

  async function confirm(confirmationId: string, code: string) {
    const body = { confirmation_id: confirmationId, code };
    onChange(await api<Application>(`${path}/sign/confirm`, { method: 'POST', body }));
  }

  return (
    <Panel title='Кредит одобрен' aside={productName}>
      <Typography.TitleResponsive className={styles.amount} tag='div' view='xlarge' font='system'>
        {formatRub(offer.amount)}
      </Typography.TitleResponsive>
      <div>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}><Term>Платёж в месяц</Term></Typography.Text>
        <Typography.Title className={styles.payment} tag='div' view='medium' font='system'>{formatRub(offer.monthly_payment)}</Typography.Title>
      </div>
      <FactRows
        rows={[
          { label: <Term>Ставка</Term>, value: `${offer.rate}%` },
          { label: 'Срок', value: formatMonths(offer.term_months) },
        ]}
      />
      <Note>Для подписи понадобится код из СМС — деньги поступят на расчётный счёт компании</Note>
      <div className={styles.sign}>
        <div className={styles.code}>
          <CodeConfirm buttonText='Подписать договор' requestCode={requestCode} confirm={confirm} />
        </div>
        <Button view='transparent' size={40} disabled={busy} onClick={decline}>
          Отказаться от кредита
        </Button>
      </div>
      {errorText}
      {footnote}
    </Panel>
  );
}
