import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, CodeRequest, Offer } from '../../api/types';
import { CodeConfirm } from '../../components/CodeConfirm';
import { OfferFacts } from './OfferFacts';
import { Term } from '../../components/Term';
import styles from './Forms.module.css';

type OfferBlockProps = {
  application: Application;
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
export function OfferBlock({ application, onChange }: OfferBlockProps) {
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
    <>
      <Gap size={8} />
      <Typography.Text view='primary-small' color='negative'>
        {error}
      </Typography.Text>
    </>
  );

  if (application.status.code === 'COUNTER_OFFER') {
    const proposed = application.offers.filter((offer) => offer.status === 'PROPOSED');
    return (
      <Plate view='common' rounded={true} border={true} title='Банк предлагает другие условия'>
        {reasons.map((reason) => (
          <Typography.Text key={reason.code} view='primary-medium' tag='p' defaultMargins={false}>
            {reason.text}
          </Typography.Text>
        ))}
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Это <Term name='Контрпредложение'>контрпредложение</Term>: условия можно принять или отказаться.
        </Typography.Text>
        <Gap size={16} />
        <div className={styles.offers}>
          {proposed.map((offer) => (
            <Plate
              key={offer.id}
              view='positive'
              rounded={true}
              title='Предложение банка'
              buttons={[
                <Button key='accept' view='accent' size={40} loading={busy} onClick={() => accept(offer)}>
                  Принять условия
                </Button>,
              ]}
            >
              <OfferFacts offer={offer} />
            </Plate>
          ))}
        </div>
        <Gap size={16} />
        <Button view='secondary' size={40} disabled={busy} onClick={decline}>
          Отказаться
        </Button>
        {errorText}
      </Plate>
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
    <Plate view='positive' rounded={true} border={true} title='Кредит одобрен'>
      <OfferFacts offer={offer} />
      <Gap size={16} />
      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
        Подпишите договор кодом — деньги поступят на расчётный счёт компании.
      </Typography.Text>
      <Gap size={12} />
      <CodeConfirm buttonText='Подписать договор' requestCode={requestCode} confirm={confirm} />
      <Gap size={12} />
      <Button view='transparent' size={32} disabled={busy} onClick={decline}>
        Отказаться от кредита
      </Button>
      {errorText}
    </Plate>
  );
}
