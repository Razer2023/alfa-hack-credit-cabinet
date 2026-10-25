import { useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, ApplicationEvent, Product } from '../../api/types';
import { ChatPanel } from '../../components/ChatPanel';
import { EventList } from '../../components/EventList';
import { ManagerContact } from '../../components/ManagerContact';
import { ApplicationSummary } from '../../components/ApplicationSummary';
import { StatusLabel } from '../../components/StatusLabel';
import { Tracker } from '../../components/Tracker';
import { useApplicationEvents } from '../../events';
import { navigate } from '../../router';
import { DraftForm } from './DraftForm';
import { NeedInfoForm } from './NeedInfoForm';
import { OfferBlock } from './OfferBlock';
import { OfferFacts } from './OfferFacts';
import { RejectionBlock } from './RejectionBlock';
import styles from './ApplicationPage.module.css';

type ApplicationPageProps = {
  id: string;
};

// Заявка клиента: что делать сейчас — слева, путь заявки и история — справа (S4.5)
export function ApplicationPage({ id }: ApplicationPageProps) {
  const [application, setApplication] = useState<Application | null>(null);
  const [events, setEvents] = useState<ApplicationEvent[]>([]);
  const [product, setProduct] = useState<Product | undefined>();
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api<Application>(`/applications/${id}`), api<ApplicationEvent[]>(`/applications/${id}/events`)])
      .then(([app, history]) => {
        setApplication(app);
        setEvents(history);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const productCode = application?.product_code;
  useEffect(() => {
    if (!productCode) return;
    api<Product[]>('/products')
      .then((products) => setProduct(products.find((item) => item.code === productCode)))
      .catch(() => undefined);
  }, [productCode]);

  // Статус меняется без перезагрузки: событие по этой заявке → перечитываем её
  useApplicationEvents((event) => {
    if (event.application_id === id) load();
  });

  // Действие на странице вернуло новую заявку: показываем её сразу, историю догружаем
  const onChange = useCallback(
    (updated: Application) => {
      setApplication(updated);
      api<ApplicationEvent[]>(`/applications/${id}/events`).then(setEvents).catch(() => undefined);
    },
    [id],
  );

  if (error) {
    return (
      <Plate view='negative' rounded={true} title='Не удалось открыть заявку'>
        {error}
      </Plate>
    );
  }
  if (!application) return <Spinner preset={48} visible={true} />;

  return (
    <>
      <Button view='transparent' size={32} onClick={() => navigate('/')}>
        ← Мои заявки
      </Button>
      <Gap size={8} />
      <div className={styles.header}>
        <Typography.Title tag='h1' view='medium' font='system'>
          Заявка {application.number}
        </Typography.Title>
        <StatusLabel status={application.status} />
      </div>
      <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
        {product?.name ?? application.product_code} · {application.status.hint}
      </Typography.Text>
      <Gap size={24} />

      <div className={styles.grid}>
        <section>
          <ApplicationSummary application={application} productName={product?.name ?? application.product_code} />
          <Gap size={24} />
          <StatusContent application={application} product={product} onChange={onChange} />
          {application.status.code !== 'DRAFT' && (
            <>
              <Gap size={24} />
              <ChatPanel
                applicationId={application.id}
                basePath='/applications'
                title={application.manager ? 'Ваш менеджер' : 'Чат с банком'}
                header={application.manager && <ManagerContact manager={application.manager} />}
              />
            </>
          )}
        </section>
        <aside>
          {application.status.code !== 'DRAFT' && application.status.code !== 'CANCELLED' && (
            <>
              <Plate view='common' rounded={true} border={true} title='Путь заявки'>
                <Tracker status={application.status.code} events={events} sla={application.status.sla} />
              </Plate>
              <Gap size={16} />
            </>
          )}
          <Plate view='common' rounded={true} border={true} title='История'>
            <EventList events={events} />
          </Plate>
        </aside>
      </div>
    </>
  );
}

type StatusContentProps = {
  application: Application;
  product: Product | undefined;
  onChange: (application: Application) => void;
};

function StatusContent({ application, product, onChange }: StatusContentProps) {
  switch (application.status.code) {
    case 'DRAFT':
      return <DraftForm application={application} product={product} onChange={onChange} />;
    case 'NEED_INFO':
      return <NeedInfoForm application={application} product={product} onChange={onChange} />;
    case 'APPROVED':
    case 'COUNTER_OFFER':
      return <OfferBlock application={application} onChange={onChange} />;
    case 'REJECTED':
      return <RejectionBlock application={application} />;
    case 'ISSUED': {
      const offer = application.offers.find((item) => item.status === 'ACCEPTED');
      return (
        <Plate view='positive' rounded={true} border={true} title='Деньги зачислены на расчётный счёт'>
          {offer && <OfferFacts offer={offer} />}
        </Plate>
      );
    }
    case 'CANCELLED':
      return (
        <Plate view='common' rounded={true} border={true} title='Заявка отменена'>
          <Typography.Text view='primary-small' color='secondary'>
            Чтобы получить кредит, оформите новую заявку из каталога.
          </Typography.Text>
        </Plate>
      );
    default:
      // SUBMITTED, CHECKING, SCORING, MANUAL_REVIEW, SIGNED — ждём банк, статус обновится сам
      return (
        <Plate view='common' rounded={true} border={true} title={application.status.title}>
          <div className={styles.waiting}>
            <Spinner preset={24} visible={true} />
            <Typography.Text view='primary-medium'>{application.status.hint}</Typography.Text>
          </div>
          <Gap size={8} />
          <Typography.Text view='primary-small' color='secondary'>
            Страницу обновлять не нужно — статус изменится автоматически.
          </Typography.Text>
        </Plate>
      );
  }
}
