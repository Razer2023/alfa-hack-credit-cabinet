import { useCallback, useEffect, useState } from 'react';
import { Accordion } from '@alfalab/core-components/accordion';
import { Button } from '@alfalab/core-components/button';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, ApplicationEvent, Product } from '../../api/types';
import { ChatPanel } from '../../components/ChatPanel';
import { EventList } from '../../components/EventList';
import { ManagerContact } from '../../components/ManagerContact';
import { StatusDot } from '../../components/StatusDot';
import { Tracker } from '../../components/Tracker';
import { useApplicationEvents } from '../../events';
import { formatMonths, formatRub } from '../../format';
import { navigate } from '../../router';
import styles from './ApplicationPage.module.css';
import { DraftForm } from './DraftForm';
import { NeedInfoForm } from './NeedInfoForm';
import { OfferBlock } from './OfferBlock';
import { OfferFacts } from './OfferFacts';
import { FactRows, Panel } from './Panel';
import { RejectionBlock } from './RejectionBlock';

type ApplicationPageProps = {
  id: string;
};

// Заявка клиента: «Что делать» слева, путь заявки и история справа, ниже — чат и вопросы (S4.5)
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

  const productName = product?.name ?? application.product_code;
  const back = (
    <Button view='text' size={32} onClick={() => navigate('/')}>
      ← Мои заявки
    </Button>
  );

  // Черновик — одна форма «Заявка на кредит для бизнеса», без пути и истории
  if (application.status.code === 'DRAFT') {
    return (
      <div className={styles.page}>
        <div className={styles.crumbs}>
          {back}
          <Typography.Text view='primary-small' color='secondary'>{application.number} · {productName}</Typography.Text>
          <StatusDot status={application.status} />
        </div>
        <DraftForm application={application} product={product} onChange={onChange} />
      </div>
    );
  }

  const showTracker = application.status.code !== 'CANCELLED';
  const wide = application.status.code === 'COUNTER_OFFER';
  const sections = [
    { id: 'todo', title: 'Что делать' },
    ...(showTracker ? [{ id: 'path', title: 'Путь заявки' }] : []),
    { id: 'chat', title: 'Чат' },
    { id: 'history', title: 'История' },
    { id: 'questions', title: 'Вопросы' },
  ];

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        {back}
        <div className={styles.title}>
          <Typography.TitleResponsive tag='h1' view='large' font='system'>
            Заявка № {application.number}
          </Typography.TitleResponsive>
          <StatusDot status={application.status} view='primary-medium' />
        </div>
        <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
          {productName} · {application.status.hint}
        </Typography.Text>
      </div>

      {/* Переход к разделам страницы: все разделы остаются на одной странице */}
      <nav className={styles.sections} aria-label='Разделы заявки'>
        {sections.map((section) => (
          <Button key={section.id} view='transparent' size={40} shape='rounded'
            onClick={() => document.getElementById(section.id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
            {section.title}
          </Button>
        ))}
      </nav>

      {/* Контрпредложение сравнивает два варианта рядом, поэтому «Что делать» — на всю ширину */}
      <div className={wide ? `${styles.grid} ${styles.wide}` : styles.grid}>
        <div id='todo' className={styles.anchor}>
          <StatusContent application={application} product={product} productName={productName} onChange={onChange} />
        </div>
        <aside className={styles.aside}>
          {showTracker && (
            <section id='path' className={`${styles.card} ${styles.anchor}`} aria-labelledby='path-title'>
              <Typography.Title id='path-title' tag='h2' view='small' font='system'>Путь заявки</Typography.Title>
              <Tracker status={application.status.code} events={events} sla={application.status.sla} />
            </section>
          )}
        </aside>
      </div>

      {/* Чат с менеджером слева, история заявки справа */}
      <div className={styles.grid}>
        <div id='chat' className={styles.anchor}>
          <ChatPanel
            applicationId={application.id}
            basePath='/applications'
            title={application.manager ? 'Ваш менеджер' : 'Чат с банком'}
            header={application.manager && <ManagerContact manager={application.manager} />}
          />
        </div>
        <section id='history' className={`${styles.card} ${styles.anchor}`} aria-labelledby='history-title'>
          <Typography.Title id='history-title' tag='h2' view='small' font='system'>История</Typography.Title>
          <EventList events={events} />
        </section>
      </div>

      <Questions />
    </div>
  );
}

type StatusContentProps = {
  application: Application;
  product: Product | undefined;
  productName: string;
  onChange: (application: Application) => void;
};

function StatusContent({ application, product, productName, onChange }: StatusContentProps) {
  switch (application.status.code) {
    case 'NEED_INFO':
      return <NeedInfoForm application={application} product={product} onChange={onChange} />;
    case 'APPROVED':
    case 'COUNTER_OFFER':
      return <OfferBlock application={application} productName={productName} onChange={onChange} />;
    case 'REJECTED':
      return <RejectionBlock application={application} />;
    case 'ISSUED': {
      const offer = application.offers.find((item) => item.status === 'ACCEPTED');
      return (
        <Panel title='Деньги зачислены на расчётный счёт' eyebrow={{ tone: 'positive', text: application.status.title }}>
          {offer && <OfferFacts offer={offer} />}
        </Panel>
      );
    }
    case 'CANCELLED':
      return (
        <Panel title='Заявка отменена'>
          <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
            Чтобы получить кредит, оформите новую заявку из каталога.
          </Typography.Text>
        </Panel>
      );
    default:
      // SUBMITTED, CHECKING, SCORING, PENDING_APPROVAL, MANUAL_REVIEW, SIGNED — ждём банк, статус обновится сам
      return (
        <Panel title={application.status.title}>
          <div className={styles.waiting}>
            <Spinner preset={24} visible={true} />
            <Typography.Text view='primary-medium'>{application.status.hint}</Typography.Text>
          </div>
          <FactRows
            rows={[
              { label: 'Запрошенная сумма', value: application.amount !== null ? formatRub(application.amount) : '—' },
              { label: 'Срок', value: application.term_months !== null ? formatMonths(application.term_months) : '—' },
              { label: 'Цель', value: application.purpose || '—' },
            ]}
          />
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            {application.status.sla ? `Обычно ${application.status.sla}. ` : ''}
            Страницу обновлять не нужно — статус изменится автоматически.
          </Typography.Text>
        </Panel>
      );
  }
}

const QUESTIONS = [
  {
    title: 'Сколько ждать решения?',
    text: 'Проверка данных и оценка занимают по 1–2 минуты. Подтверждение сотрудником банка — до 2 часов в рабочее время, у кредитного специалиста — до 1 рабочего дня. Статус обновляется сам.',
  },
  {
    title: 'Какие документы могут понадобиться?',
    text: 'Обычно хватает ИНН: данные компании подтягиваются из ЕГРЮЛ, ФНС и выписки по счёту. Если банку нужно больше, он попросит документ прямо в заявке — статус сменится на «Нужны данные».',
  },
  {
    title: 'Что делать, если отказали?',
    text: 'В заявке будут причины отказа и что можно сделать. Шансы на другую сумму можно оценить по ИНН в разделе «Кредитные продукты» — это не новая заявка.',
  },
  {
    title: 'Как связаться с менеджером?',
    text: 'Напишите в чат на этой странице — менеджер ответит здесь же. Его телефон и часы работы — над перепиской.',
  },
  {
    title: 'Что такое контрпредложение?',
    text: 'Если запрошенные условия не проходят, банк предлагает другие: меньшую сумму или более длинный срок. Их можно принять или отказаться.',
  },
];

// «Вопросы по заявке» — справка без запросов к API
function Questions() {
  // Открыт первый вопрос, остальные — по нажатию
  const [open, setOpen] = useState<Set<string>>(() => new Set([QUESTIONS[0].title]));
  const toggle = (title: string, expanded: boolean) =>
    setOpen((current) => {
      const next = new Set(current);
      if (expanded) next.add(title);
      else next.delete(title);
      return next;
    });

  return (
    <section id='questions' className={`${styles.questions} ${styles.anchor}`} aria-labelledby='questions-title'>
      <Typography.TitleResponsive id='questions-title' tag='h2' view='medium' font='system'>
        Вопросы по заявке
      </Typography.TitleResponsive>
      <div className={styles.accordion}>
        {QUESTIONS.map((question) => {
          const expanded = open.has(question.title);
          return (
            <Accordion
              key={question.title}
              className={styles.question}
              containerClassName={styles.questionHeader}
              headerClassName={styles.questionTitle}
              bodyContentClassName={styles.questionBody}
              expanded={expanded}
              onExpandedChange={(value) => toggle(question.title, value)}
              control={
                <Typography.Text className={styles.questionControl} view='primary-large' color='secondary' aria-hidden='true'>
                  {expanded ? '−' : '+'}
                </Typography.Text>
              }
              header={<Typography.TitleResponsive tag='h3' view='small' font='system'>{question.title}</Typography.TitleResponsive>}
            >
              <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
                {question.text}
              </Typography.Text>
            </Accordion>
          );
        })}
      </div>
    </section>
  );
}
