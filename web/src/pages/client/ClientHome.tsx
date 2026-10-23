import { useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, ApplicationEvent, Product } from '../../api/types';
import { ApplicationSummary } from '../../components/ApplicationSummary';
import { Money } from '../../components/Money';
import { StatusLabel } from '../../components/StatusLabel';
import { Tracker } from '../../components/Tracker';
import { useApplicationEvents } from '../../events';
import { formatDateTime } from '../../format';
import { navigate, useRoute } from '../../router';
import styles from './ClientHome.module.css';
import { ProductCard } from './ProductCard';

const TERMINAL = new Set(['ISSUED', 'REJECTED', 'CANCELLED']);

export function ClientHome() {
  const showProducts = useRoute() === '/products';
  const [products, setProducts] = useState<Product[]>([]);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [creating, setCreating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<{ id: string; events: ApplicationEvent[] } | null>(null);
  const [historyError, setHistoryError] = useState<string | null>(null);

  const loadApplications = useCallback(() => {
    api<Application[]>('/applications').then(setApplications).catch((e) => setError(errorMessage(e)));
  }, []);

  useEffect(() => {
    api<Product[]>('/products').then(setProducts).catch((e) => setError(errorMessage(e)));
    loadApplications();
  }, [loadApplications]);
  useApplicationEvents(loadApplications);

  const ordered = [...(applications ?? [])].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  const featured = ordered.find((app) => !TERMINAL.has(app.status.code)) ?? ordered[0];
  const featuredId = featured?.id;
  const featuredUpdatedAt = featured?.updated_at;
  useEffect(() => {
    if (!featuredId) return;
    let current = true;
    api<ApplicationEvent[]>(`/applications/${featuredId}/events`)
      .then((events) => { if (current) { setHistory({ id: featuredId, events }); setHistoryError(null); } })
      .catch((e) => { if (current) setHistoryError(errorMessage(e)); });
    return () => { current = false; };
  }, [featuredId, featuredUpdatedAt]);

  async function apply(product: Product) {
    setCreating(product.code);
    setError(null);
    try {
      const created = await api<Application>('/applications', { method: 'POST', body: { product_code: product.code } });
      navigate(`/applications/${created.id}`);
    } catch (e) {
      setError(errorMessage(e));
      setCreating(null);
    }
  }

  const productName = (code: string) => products.find((product) => product.code === code)?.name ?? code;
  const events = history && history.id === featuredId ? history.events : null;

  return (
    <>
      <div className={styles.heading}>
        <div>
          <Typography.Text view='primary-small' color='secondary'>Кабинет предпринимателя</Typography.Text>
          <Gap size={8} />
          <Typography.Title tag='h1' view='large' font='system'>
            {showProducts ? 'Кредит под вашу задачу' : 'Бизнес движется вперёд.'}
          </Typography.Title>
          <Gap size={8} />
          <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
            {showProducts ? 'Сравните суммы, сроки и условия финансирования.' : 'Заявка, решение и следующие шаги — здесь.'}
          </Typography.Text>
        </div>
        {!showProducts && <Button view='accent' size={48} href='#/products'>Выбрать кредит</Button>}
      </div>
      {error && <div role='alert' className={styles.error}><Plate view='negative' rounded={true} title='Не удалось загрузить данные'>{error}</Plate></div>}
      {showProducts ? (
        <>
          {products.length === 0 && !error && <Spinner preset={24} visible={true} />}
          <div className={styles.catalog}>
            {products.map((product) => (
              <ProductCard key={product.code} product={product} loading={creating === product.code}
                disabled={creating !== null} onApply={() => apply(product)} />
            ))}
          </div>
        </>
      ) : applications === null ? (
        !error && <Spinner preset={48} visible={true} />
      ) : featured ? (
        <div className={styles.overview}>
          <div className={styles.primary}>
            <ApplicationSummary application={featured} productName={productName(featured.product_code)} onOpen={() => navigate(`/applications/${featured.id}`)} />
            <section className={styles.applications} aria-label='Мои заявки'>
              <Typography.Title tag='h2' view='xsmall' font='system'>Мои заявки</Typography.Title>
              {ordered.map((application) => (
                <div key={application.id} className={styles.row}>
                  <div className={styles.rowTitle}>
                    <Button view='text' size={40} href={`#/applications/${application.id}`}>{application.number}</Button>
                    <Typography.Text view='primary-small'>{productName(application.product_code)}</Typography.Text>
                    <Typography.Text view='secondary-large' color='secondary'>{formatDateTime(application.status_changed_at)}</Typography.Text>
                  </div>
                  <div className={styles.rowMeta}>
                    <Typography.Text view='primary-medium' weight='bold'>{application.amount !== null ? <Money value={application.amount} /> : 'Сумма не указана'}</Typography.Text>
                    <StatusLabel status={application.status} />
                  </div>
                </div>
              ))}
            </section>
          </div>
          <aside className={styles.timeline}>
            <Typography.Title tag='h2' view='xsmall' font='system'>Путь заявки</Typography.Title>
            <Gap size={20} />
            {historyError ? <Typography.Text view='primary-small' color='negative'>{historyError}</Typography.Text>
              : events === null ? <Spinner preset={24} visible={true} />
              : featured.status.code === 'DRAFT' || featured.status.code === 'CANCELLED'
                ? <Typography.Text view='primary-medium'>{featured.status.hint}</Typography.Text>
                : <Tracker status={featured.status.code} events={events} />}
            <Gap size={16} />
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>Изменения статуса появляются автоматически.</Typography.Text>
          </aside>
        </div>
      ) : (
        <Plate view='common' rounded={true} title='Начните с выбора кредита'
          buttons={[<Button key='products' view='accent' size={48} href='#/products'>Посмотреть продукты</Button>]}>
          <Typography.Text view='primary-medium' color='secondary'>Здесь появятся ваши заявки, решения банка и следующие шаги.</Typography.Text>
        </Plate>
      )}
    </>
  );
}
