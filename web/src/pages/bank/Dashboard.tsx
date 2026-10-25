import { useCallback, useEffect, useState } from 'react';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Status } from '@alfalab/core-components/status';
import { TBody, TCell, THead, THeadCell, TRow, Table } from '@alfalab/core-components/table';
import { Tab, Tabs, type TabsProps } from '@alfalab/core-components/tabs';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Dashboard as DashboardData, DashboardStage } from '../../api/types';
import { useApplicationEvents } from '../../events';
import { STATUS_COLOR } from '../../format';
import styles from './Dashboard.module.css';

const SOURCES: Record<string, string> = {
  LIVE: 'Живые заявки',
  DEMO: 'Демо-массив',
};
const OWNER: Record<DashboardStage['owner'], string> = {
  SYSTEM: 'Автоматика',
  BANK: 'Банк',
  CLIENT: 'Клиент',
};

function formatMinutes(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  if (value < 1) return 'меньше минуты';
  if (value < 60) return `${Math.round(value)} мин`;
  if (value < 24 * 60) {
    const hours = Math.floor(value / 60);
    const minutes = Math.round(value % 60);
    return minutes ? `${hours} ч ${minutes} мин` : `${hours} ч`;
  }
  return `${Math.round(value / (24 * 60))} дн`;
}

// Дашборд узких мест (S8.1): где заявки теряют время и где нарушен обещанный срок
export function Dashboard() {
  const [source, setSource] = useState<TabsProps['selectedId']>('LIVE');
  // По источнику отдельно: запоздавший ответ другой вкладки не затирает выбранную
  const [data, setData] = useState<Partial<Record<DashboardData['source'], DashboardData>>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api<DashboardData>(`/bank/dashboard?source=${source}`)
      .then((value) => {
        setData((current) => ({ ...current, [value.source]: value }));
        setError(null);
      })
      .catch((e) => setError(errorMessage(e)));
  }, [source]);

  useEffect(() => {
    load();
  }, [load]);

  // Живые цифры пересчитываются при каждом изменении заявок
  useApplicationEvents(() => {
    if (source === 'LIVE') load();
  });

  const current = data[source as DashboardData['source']] ?? null;
  const bankTime = current?.stages.filter((stage) => stage.owner !== 'CLIENT') ?? [];
  const maxTotal = Math.max(1, ...bankTime.map((stage) => stage.total_minutes));

  const content = (
    <>
      <Gap size={16} />
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
      {current && (
        <>
          <Plate
            view={current.bottleneck ? 'attention' : 'common'}
            rounded={true}
            border={true}
            title={current.bottleneck ? 'Узкое место' : 'Узких мест не видно'}
          >
            <Typography.Text view='primary-medium' tag='p' defaultMargins={false}>
              {current.bottleneck_text ?? 'Заявок, прошедших этапы банка, пока нет.'}
            </Typography.Text>
          </Plate>
          <Gap size={16} />
          <div className={styles.summary}>
            <Typography.Text view='primary-medium' weight='bold'>
              Заявок: {current.applications}
            </Typography.Text>
            {current.by_status.map((item) => (
              <Status key={item.code} view='soft' color={STATUS_COLOR[item.code]} size={20}>
                {item.title}: {item.count}
              </Status>
            ))}
          </div>
          <Gap size={16} />
          <Table>
            <THead>
              <THeadCell>Этап</THeadCell>
              <THeadCell>Кто отвечает</THeadCell>
              <THeadCell textAlign='right'>Прошли</THeadCell>
              <THeadCell textAlign='right'>Обычно</THeadCell>
              <THeadCell textAlign='right'>90 % быстрее</THeadCell>
              <THeadCell textAlign='right'>Сейчас</THeadCell>
              <THeadCell textAlign='right'>Вне срока</THeadCell>
              <THeadCell>Доля времени банка</THeadCell>
            </THead>
            <TBody>
              {current.stages.map((stage) => (
                <TRow key={stage.code} className={stage.code === current.bottleneck ? styles.bottleneck : undefined}>
                  <TCell>
                    <Typography.Text view='primary-small' weight='bold' tag='p' defaultMargins={false}>
                      {stage.title}
                    </Typography.Text>
                    {stage.sla && (
                      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                        Срок: {stage.sla}
                      </Typography.Text>
                    )}
                  </TCell>
                  <TCell>{OWNER[stage.owner]}</TCell>
                  <TCell className={styles.number}>{stage.passed}</TCell>
                  <TCell className={styles.number}>{formatMinutes(stage.median_minutes)}</TCell>
                  <TCell className={styles.number}>{formatMinutes(stage.p90_minutes)}</TCell>
                  <TCell className={styles.number}>
                    {stage.in_progress > 0
                      ? `${stage.in_progress}, дольше всех ${formatMinutes(stage.longest_wait_minutes)}`
                      : '—'}
                  </TCell>
                  <TCell className={styles.number}>
                    {stage.over_sla > 0 ? (
                      <Status view='soft' color='red' size={20}>
                        {stage.over_sla}
                      </Status>
                    ) : (
                      '—'
                    )}
                  </TCell>
                  <TCell>
                    {stage.owner === 'CLIENT' ? (
                      <Typography.Text view='primary-small' color='secondary'>
                        ждём клиента
                      </Typography.Text>
                    ) : (
                      <div className={styles.bar} aria-label={`${Math.round((100 * stage.total_minutes) / maxTotal)} % от самого долгого этапа`}>
                        <span style={{ width: `${(100 * stage.total_minutes) / maxTotal}%` }} />
                      </div>
                    )}
                  </TCell>
                </TRow>
              ))}
            </TBody>
          </Table>
          <Gap size={12} />
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            {current.source === 'LIVE'
              ? 'По журналу событий ядра: время статуса — до следующего перехода, у заявок в работе — до текущего момента.'
              : 'Синтетический массив сервиса интеграций: заранее посчитанные длительности этапов, чтобы показать дашборд на объёме.'}
          </Typography.Text>
        </>
      )}
    </>
  );

  return (
    <>
      <Typography.Title tag='h1' view='medium' font='system'>
        Узкие места процесса
      </Typography.Title>
      <Gap size={16} />
      <Tabs view='primary' size='s' selectedId={source} onChange={(_, { selectedId }) => setSource(selectedId)}>
        {Object.entries(SOURCES).map(([id, title]) => (
          <Tab key={id} id={id} title={title}>
            {id === source ? content : null}
          </Tab>
        ))}
      </Tabs>
    </>
  );
}
