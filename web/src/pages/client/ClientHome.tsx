import { useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, Product } from '../../api/types';
import { Money } from '../../components/Money';
import { StageBar } from '../../components/StageBar';
import { StatusDot } from '../../components/StatusDot';
import { useApplicationEvents } from '../../events';
import { formatDateTime, formatMonths, formatRub } from '../../format';
import { Hero, Sheet } from '../../layout/Page';
import { useRoute } from '../../router';
import { nextStep, stageLabel } from '../../stages';
import { useInvertedOnDark } from '../../theme/ThemeContext';
import { Catalog } from './Catalog';
import styles from './ClientHome.module.css';
import { HowItWorks } from './HowItWorks';

const TERMINAL = new Set(['ISSUED', 'REJECTED', 'CANCELLED']);

export function ClientHome() {
  return useRoute() === '/products' ? <Catalog /> : <Overview />;
}

// Обзор клиента (S4.5): главная заявка на тёмном первом экране, ниже — все заявки
function Overview() {
  const [products, setProducts] = useState<Product[]>([]);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inverted = useInvertedOnDark();

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
  const productName = (code: string) => products.find((product) => product.code === code)?.name ?? code;

  const errorPlate = error && (
    <div role='alert' className={styles.error}>
      <Plate view='negative' rounded={true} title='Не удалось загрузить данные'>{error}</Plate>
    </div>
  );

  if (applications === null) {
    return (
      <>
        <Hero>{error ? null : <Spinner preset={48} visible={true} colors={inverted ? 'inverted' : 'default'} />}</Hero>
        <Sheet>{errorPlate}</Sheet>
      </>
    );
  }

  if (!featured) {
    return (
      <>
        <Hero className={styles.empty}>
          <Typography.TitleResponsive tag='h1' view='xlarge' font='system' color='primary-inverted'>
            Начните с выбора кредита
          </Typography.TitleResponsive>
          <Typography.Text view='primary-medium' color='secondary-inverted' tag='p' defaultMargins={false}>
            Здесь появятся ваши заявки, решения банка и следующие шаги.
          </Typography.Text>
          <div className={styles.actions}>
            <Button view='accent' size={56} href='#/products'>Посмотреть продукты</Button>
            <Typography.Text className={styles.pill} view='primary-small' color='secondary-inverted'>
              Шансы можно оценить по ИНН — это не заявка
            </Typography.Text>
          </div>
        </Hero>
        <Sheet>
          {errorPlate}
          <HowItWorks />
        </Sheet>
      </>
    );
  }

  return (
    <>
      <Hero>
        <FeaturedApplication application={featured} productName={productName(featured.product_code)} />
      </Hero>
      <Sheet>
        {errorPlate}
        <section className={styles.list} aria-labelledby='my-applications'>
          <div className={styles.listHeading}>
            <Typography.Title id='my-applications' tag='h2' view='small' font='system'>Мои заявки</Typography.Title>
            <Typography.Text view='primary-small' color='secondary'>Статусы обновляются автоматически</Typography.Text>
          </div>
          <ul className={styles.rows}>
            {ordered.map((application) => (
              <li key={application.id}>
                <a className={styles.row} href={`#/applications/${application.id}`}>
                  <span className={styles.rowTitle}>
                    <Typography.Text view='primary-medium' weight='medium'>
                      {application.number} · {productName(application.product_code)}
                    </Typography.Text>
                    <Typography.Text view='primary-small' color='secondary'>
                      изменена {formatDateTime(application.status_changed_at)}
                    </Typography.Text>
                  </span>
                  <StageBar className={styles.rowStages} status={application.status.code} />
                  <Typography.Text className={styles.rowAmount} view='primary-medium' weight='bold'
                    color={application.amount === null ? 'secondary' : 'primary'}>
                    {application.amount !== null ? <Money value={application.amount} bold={true} /> : 'Сумма не указана'}
                  </Typography.Text>
                  <StatusDot status={application.status} />
                </a>
              </li>
            ))}
          </ul>
        </section>
      </Sheet>
    </>
  );
}

type FeaturedApplicationProps = {
  application: Application;
  productName: string;
};

// Главная заявка: сумма, статус, главное действие и три карточки — следующий шаг, путь, менеджер
function FeaturedApplication({ application, productName }: FeaturedApplicationProps) {
  const actions = application.allowed_actions;
  const href = `#/applications/${application.id}`;
  const action = actions.includes('SIGN') ? 'Подписать договор'
    : actions.includes('ACCEPT_OFFER') ? 'Посмотреть условия'
    : actions.includes('PROVIDE_INFO') ? 'Дополнить заявку'
    : actions.includes('EDIT') ? 'Продолжить заполнение'
    : null;
  const details = [
    application.term_months !== null && `на ${formatMonths(application.term_months)}`,
    application.purpose,
  ].filter(Boolean).join(' · ');
  const manager = application.manager;
  const inverted = useInvertedOnDark();

  return (
    <div className={styles.featured}>
      <div className={styles.featuredTop}>
        <div className={styles.featuredText}>
          <Typography.Text view='primary-medium' color='secondary-inverted'>
            Заявка № {application.number} · {productName}
          </Typography.Text>
          <Typography.TitleResponsive className={styles.amount} tag='div' view='xlarge' font='system' color='primary-inverted'>
            {application.amount !== null ? formatRub(application.amount) : 'Сумма не указана'}
          </Typography.TitleResponsive>
          <Typography.Text view='primary-medium' color='secondary-inverted'>{details || 'Цель пока не указана'}</Typography.Text>
        </div>
        <StatusDot status={application.status} inverted={true} view='primary-medium' />
      </div>

      <div className={styles.actions}>
        {action
          ? <Button view='accent' size={56} href={href}>{action}</Button>
          : <Button view='secondary' colors={inverted ? 'inverted' : 'default'} size={56} href={href}>Открыть заявку</Button>}
        <Typography.Text className={styles.pill} view='primary-small' color='secondary-inverted'>
          {application.status.hint}
          {application.status.sla && <><br />Обычно {application.status.sla}</>}
        </Typography.Text>
      </div>

      <div className={manager ? styles.cards : `${styles.cards} ${styles.twoCards}`}>
        <div className={styles.card}>
          <Typography.Text view='primary-medium' weight='bold' color='primary-inverted'>Следующий шаг</Typography.Text>
          <Typography.Text view='primary-small' color='secondary-inverted'>{nextStep(application)}</Typography.Text>
        </div>
        <div className={styles.card}>
          <Typography.Text view='primary-medium' weight='bold' color='primary-inverted'>Путь заявки</Typography.Text>
          <StageBar className={styles.cardStages} status={application.status.code} inverted={true} />
          <Typography.Text view='primary-small' color='secondary-inverted'>{stageLabel(application.status.code)}</Typography.Text>
        </div>
        {manager && (
          <div className={styles.card}>
            <Typography.Text view='primary-medium' weight='bold' color='primary-inverted'>Ваш менеджер</Typography.Text>
            <Typography.Text view='primary-small' color='primary-inverted'>{manager.full_name}</Typography.Text>
            <Typography.Text view='primary-small' color='secondary-inverted'>
              {[manager.phone, manager.work_hours].filter(Boolean).join(' · ') || manager.position}
            </Typography.Text>
          </div>
        )}
      </div>
    </div>
  );
}
