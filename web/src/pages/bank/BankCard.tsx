import { useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { Status } from '@alfalab/core-components/status';
import { TBody, TCell, THead, THeadCell, TRow, Table } from '@alfalab/core-components/table';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { ApplicationEvent, BankApplication } from '../../api/types';
import { useUser } from '../../auth/AuthContext';
import { CompanyFacts } from '../../components/CompanyFacts';
import { EventList } from '../../components/EventList';
import { FactList } from '../../components/FactList';
import { Money } from '../../components/Money';
import { StatusLabel } from '../../components/StatusLabel';
import { useApplicationEvents } from '../../events';
import { formatDateTime, formatMonths } from '../../format';
import { navigate } from '../../router';
import { OfferFacts } from '../client/OfferFacts';
import { DecisionForm } from './DecisionForm';
import { InfoRequestForm } from './InfoRequestForm';
import styles from './Bank.module.css';

const RESULT_TITLE: Record<string, string> = {
  APPROVE: 'Одобрить',
  COUNTER_OFFER: 'Контрпредложение',
  REJECT: 'Отказ',
  MANUAL_REVIEW: 'Ручное рассмотрение',
};

type BankCardProps = {
  id: string;
};

// Карточка андеррайтера (S5.3): анкета, внешние проверки, скоринг, история и решение
export function BankCard({ id }: BankCardProps) {
  const user = useUser();
  const [application, setApplication] = useState<BankApplication | null>(null);
  const [events, setEvents] = useState<ApplicationEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([api<BankApplication>(`/bank/applications/${id}`), api<ApplicationEvent[]>(`/bank/applications/${id}/events`)])
      .then(([card, history]) => {
        setApplication(card);
        setEvents(history);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  useApplicationEvents((event) => {
    if (event.application_id === id) load();
  });

  const onChange = useCallback(
    (updated: BankApplication) => {
      setApplication(updated);
      api<ApplicationEvent[]>(`/bank/applications/${id}/events`).then(setEvents).catch(() => undefined);
    },
    [id],
  );

  async function act(path: string, body?: unknown) {
    setBusy(true);
    setError(null);
    try {
      onChange(await api<BankApplication>(`/bank/applications/${id}/${path}`, { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  const take = () => act('take');
  const escalate = () => act('escalate', { comment: null });

  if (error && !application) {
    return (
      <Plate view='negative' rounded={true} title='Не удалось открыть заявку'>
        {error}
      </Plate>
    );
  }
  if (!application) return <Spinner preset={48} visible={true} />;

  const actions = application.allowed_actions;
  const pending = application.status.code === 'PENDING_APPROVAL';
  const { enrichment, scoring } = application;
  const extra = Object.entries(application.form.extra ?? {});

  return (
    <>
      <Button view='transparent' size={32} onClick={() => navigate('/')}>
        ← Очередь заявок
      </Button>
      <Gap size={8} />
      <div className={styles.header}>
        <Typography.Title tag='h1' view='medium' font='system'>
          {application.number} · {application.company.name}
        </Typography.Title>
        <StatusLabel status={application.status} />
        {actions.includes('TAKE') && application.assignee_id !== user.id && (
          <Button view='secondary' size={32} loading={busy} onClick={take}>
            Взять в работу
          </Button>
        )}
        {application.assignee_id === user.id && (
          <Status view='muted-alt' color='blue'>
            В работе у вас
          </Status>
        )}
      </div>
      <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
        ИНН {application.company.inn} · {application.status.hint}
        {application.manager && ` · ведёт ${application.manager.full_name}`}
        {application.status.due_at && ` · срок до ${formatDateTime(application.status.due_at)}`}
      </Typography.Text>
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
      <Gap size={24} />

      {/* Рекомендацию скоринга подтверждает менеджер или андеррайтер; рисковые заявки и отказ — только андеррайтер */}
      {actions.includes('DECIDE') && (pending || user.role === 'UNDERWRITER') && (
        <>
          <Plate
            view='attention'
            rounded={true}
            border={true}
            title={pending ? 'Подтверждение одобрения' : 'Решение по заявке'}
          >
            <DecisionForm application={application} canReject={user.role === 'UNDERWRITER'} onChange={onChange} />
            {actions.includes('ESCALATE') && user.role === 'MANAGER' && (
              <>
                <Gap size={12} />
                <Button view='transparent' size={32} loading={busy} onClick={escalate}>
                  Сомневаюсь — передать андеррайтеру
                </Button>
              </>
            )}
          </Plate>
          <Gap size={16} />
        </>
      )}
      {actions.includes('REQUEST_INFO') && (
        <>
          <Plate view='common' rounded={true} border={true} title='Запросить данные у клиента' foldable={true} defaultFolded={true}>
            <InfoRequestForm application={application} onChange={onChange} />
          </Plate>
          <Gap size={16} />
        </>
      )}

      <div className={styles.grid}>
        <div>
          <Plate view='common' rounded={true} border={true} title='Заявка'>
            <FactList
              facts={[
                { label: 'Продукт', value: application.product_code },
                { label: 'Сумма', value: application.amount ? <Money value={application.amount} bold={true} /> : '—' },
                { label: 'Срок', value: application.term_months ? formatMonths(application.term_months) : '—' },
                { label: 'Цель', value: application.purpose ?? '—' },
                { label: 'Отправлена', value: application.submitted_at ? formatDateTime(application.submitted_at) : '—' },
                ...extra.map(([field, value], index) => ({
                  label: extra.length > 1 ? `Ответ клиента ${index + 1}` : 'Ответ клиента',
                  value: <span title={field}>{String(value)}</span>,
                })),
              ]}
            />
          </Plate>
          <Gap size={16} />
          <Plate view='common' rounded={true} border={true} title='Компания'>
            {application.form.company ? (
              <CompanyFacts company={application.form.company} />
            ) : (
              <Typography.Text view='primary-small' color='secondary'>
                Клиент не заполнил данные по ИНН
              </Typography.Text>
            )}
          </Plate>
          {application.offers.length > 0 && (
            <>
              <Gap size={16} />
              {application.offers.map((offer) => (
                <div key={offer.id}>
                  <Plate
                    view='common'
                    rounded={true}
                    border={true}
                    title={offer.kind === 'COUNTER' ? 'Контрпредложение' : 'Предложение'}
                  >
                    <OfferFacts offer={offer} />
                  </Plate>
                  <Gap size={8} />
                </div>
              ))}
            </>
          )}
        </div>

        <div>
          <Plate view='common' rounded={true} border={true} title='Внешние проверки'>
            {enrichment ? (
              <FactList
                facts={[
                  { label: 'ЕГРЮЛ: статус', value: enrichment.egrul.status },
                  { label: 'ЕГРЮЛ: ликвидация', value: <Flag bad={enrichment.egrul.liquidation} /> },
                  { label: 'ФНС: долг по налогам', value: <Money value={enrichment.fns.tax_debt} /> },
                  { label: 'ФНС: массовый адрес', value: <Flag bad={enrichment.fns.mass_address} /> },
                  {
                    label: 'БКИ: макс. просрочка',
                    value: (
                      <span className={enrichment.bki.max_overdue_days > 0 ? styles.negative : undefined}>
                        {enrichment.bki.max_overdue_days} дн.
                      </span>
                    ),
                  },
                  { label: 'БКИ: действующих кредитов', value: enrichment.bki.active_loans },
                  { label: 'БКИ: общий долг', value: <Money value={enrichment.bki.total_debt} /> },
                ]}
              />
            ) : (
              <Typography.Text view='primary-small' color='secondary'>
                Проверки ещё не выполнены
              </Typography.Text>
            )}
          </Plate>
          <Gap size={16} />
          <Plate view='common' rounded={true} border={true} title='Скоринг'>
            {scoring ? (
              <>
                <div className={styles.score}>
                  <ScoreValue label='Балл' value={scoring.score} />
                  <ScoreValue label='Класс риска' value={scoring.risk_class} />
                  <ScoreValue label='Рекомендация' value={RESULT_TITLE[scoring.result] ?? scoring.result} />
                </div>
                <Gap size={12} />
                {(scoring.factors ?? []).length > 0 && (
                  <Table compactView={true}>
                    <THead>
                      <THeadCell>Фактор</THeadCell>
                      <THeadCell>Значение</THeadCell>
                      <THeadCell textAlign='right'>Баллы</THeadCell>
                    </THead>
                    <TBody>
                      {(scoring.factors ?? []).map((factor) => (
                        <TRow key={factor.code}>
                          <TCell className={styles.wrap}>{factor.title}</TCell>
                          <TCell className={styles.wrap}>{factor.value ?? '—'}</TCell>
                          <TCell className={factor.impact < 0 ? styles.negative : styles.positive}>
                            {factor.impact > 0 ? `+${factor.impact}` : factor.impact}
                          </TCell>
                        </TRow>
                      ))}
                    </TBody>
                  </Table>
                )}
                {(scoring.reasons ?? []).map((reason) => (
                  <Typography.Text key={reason.code} view='primary-small' tag='p' defaultMargins={false}>
                    • {reason.text}
                  </Typography.Text>
                ))}
                {scoring.metrics?.dscr != null && (
                  <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                    DSCR {scoring.metrics.dscr} при минимуме {scoring.metrics.min_dscr}
                  </Typography.Text>
                )}
                <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                  Модель {scoring.model_version}
                </Typography.Text>
              </>
            ) : (
              <Typography.Text view='primary-small' color='secondary'>
                Скоринг ещё не проводился
              </Typography.Text>
            )}
          </Plate>
          <Gap size={16} />
          <Plate view='common' rounded={true} border={true} title='История'>
            <EventList events={events} />
          </Plate>
        </div>
      </div>
    </>
  );
}

function Flag({ bad }: { bad: boolean }) {
  return <span className={bad ? styles.negative : undefined}>{bad ? 'да' : 'нет'}</span>;
}

function ScoreValue({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
        {label}
      </Typography.Text>
      <Typography.Title tag='div' view='small' font='system'>
        {value}
      </Typography.Title>
    </div>
  );
}
