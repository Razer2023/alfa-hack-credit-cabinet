import { useCallback, useEffect, useState } from 'react';
import { Gap } from '@alfalab/core-components/gap';
import { TBody, TCell, THead, THeadCell, TRow, Table } from '@alfalab/core-components/table';
import { Tab, Tabs, type TabsProps } from '@alfalab/core-components/tabs';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { BankApplication } from '../../api/types';
import { Money } from '../../components/Money';
import { StatusLabel } from '../../components/StatusLabel';
import { useApplicationEvents } from '../../events';
import { formatDateTime } from '../../format';
import { navigate } from '../../router';
import styles from './Bank.module.css';

const FILTERS: Record<string, { title: string; query: string }> = {
  review: { title: 'Ждут решения', query: '?status=PENDING_APPROVAL&status=MANUAL_REVIEW' },
  active: {
    title: 'В работе',
    query: '?status=SUBMITTED&status=CHECKING&status=NEED_INFO&status=SCORING&status=APPROVED&status=COUNTER_OFFER&status=SIGNED',
  },
  mine: { title: 'Мои', query: '?mine=true' },
  all: { title: 'Все', query: '' },
};

// Очередь заявок менеджера и андеррайтера (S4.3)
export function BankHome() {
  const [filter, setFilter] = useState<TabsProps['selectedId']>('review');
  const [applications, setApplications] = useState<BankApplication[]>([]);
  const [error, setError] = useState<string | null>(null);
  const query = FILTERS[String(filter)].query;

  const load = useCallback(() => {
    api<BankApplication[]>(`/bank/applications${query}`)
      .then((items) => {
        setApplications(items);
        setError(null);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [query]);

  useEffect(() => {
    load();
  }, [load]);

  // Очередь обновляется сама при любом изменении заявок
  useApplicationEvents(load);

  const table = (
    <>
      <Gap size={16} />
      {error && (
        <Typography.Text view='primary-small' color='negative'>
          {error}
        </Typography.Text>
      )}
      {applications.length === 0 ? (
        <Typography.Text view='primary-medium' color='secondary'>
          Заявок нет
        </Typography.Text>
      ) : (
        <Table>
          <THead>
            <THeadCell>Номер</THeadCell>
            <THeadCell>Компания</THeadCell>
            <THeadCell textAlign='right'>Сумма</THeadCell>
            <THeadCell>Срок</THeadCell>
            <THeadCell>Статус</THeadCell>
            <THeadCell>Изменена</THeadCell>
          </THead>
          <TBody>
            {applications.map((application) => (
              <TRow key={application.id} className={styles.row} onClick={() => navigate(`/bank/${application.id}`)}>
                <TCell>{application.number}</TCell>
                <TCell>{application.company.name}</TCell>
                <TCell className={styles.amount}>{application.amount ? <Money value={application.amount} /> : '—'}</TCell>
                <TCell>{application.term_months ? `${application.term_months} мес.` : '—'}</TCell>
                <TCell>
                  <StatusLabel status={application.status} />
                </TCell>
                <TCell>{formatDateTime(application.status_changed_at)}</TCell>
              </TRow>
            ))}
          </TBody>
        </Table>
      )}
    </>
  );

  return (
    <>
      <Typography.Title tag='h1' view='medium' font='system'>
        Заявки малого бизнеса
      </Typography.Title>
      <Gap size={16} />
      <Tabs view='primary' size='s' selectedId={filter} onChange={(_, { selectedId }) => setFilter(selectedId)}>
        {Object.entries(FILTERS).map(([id, { title }]) => (
          <Tab key={id} id={id} title={title}>
            {id === filter ? table : null}
          </Tab>
        ))}
      </Tabs>
    </>
  );
}
