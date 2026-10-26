import { type ReactNode, useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Dashboard as DashboardData, DashboardStage } from '../../api/types';
import { useApplicationEvents } from '../../events';
import styles from './Dashboard.module.css';

type Source = DashboardData['source'];
type Metric = 'median' | 'p90';

const SOURCES: Record<Source, string> = {
  LIVE: 'Живые заявки',
  DEMO: 'Демо-массив',
};
const OWNER: Record<DashboardStage['owner'], string> = {
  SYSTEM: 'Автоматика',
  BANK: 'Банк',
  CLIENT: 'Клиент',
};
// Цвета долей на диаграмме статусов — по порядку, токены дизайн-системы
const PALETTE = [
  'var(--color-light-accent-primary)',
  'var(--color-light-status-info)',
  'var(--color-light-status-positive)',
  'var(--color-light-status-attention)',
  'var(--color-light-graphic-secondary)',
  'var(--color-light-graphic-negative-tint-30)',
  'var(--color-light-graphic-positive-shade-30)',
  'var(--color-light-graphic-tertiary)',
];

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

// Подписи диаграммы: короткие значения — в секундах, чтобы шкала не сливалась в «меньше минуты»
function formatTick(value: number): string {
  if (value > 0 && value < 1) return `${Math.max(1, Math.round(value * 60))} с`;
  return formatMinutes(value);
}

// Аналитика (S8.1), в общей теме кабинета: где заявки теряют время и где нарушен обещанный срок
export function Dashboard() {
  const [source, setSource] = useState<Source>('LIVE');
  // По источнику отдельно: запоздавший ответ другой вкладки не затирает выбранную
  const [data, setData] = useState<Partial<Record<Source, DashboardData>>>({});
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

  const current = data[source] ?? null;

  return (
    <div className={styles.page}>
      <div className={styles.container}>
        <header className={styles.heading}>
          <div>
            <Typography.TitleResponsive tag='h1' view='large' font='system' color='primary'>
              Аналитика
            </Typography.TitleResponsive>
            <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
              Где заявки теряют время и где нарушен обещанный срок
            </Typography.Text>
          </div>
          <div className={styles.switch} role='group' aria-label='Источник данных'>
            {(Object.keys(SOURCES) as Source[]).map((id) => (
              <Button key={id} view={id === source ? 'secondary' : 'transparent'} size={40}
                shape='rounded' aria-pressed={id === source} onClick={() => setSource(id)}>
                {SOURCES[id]}
              </Button>
            ))}
          </div>
        </header>

        {error && (
          <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
            {error}
          </Typography.Text>
        )}

        {current && (
          <>
            <div className={styles.grid}>
              <div className={styles.column}>
                <StageChart data={current} />
                <StatusDonut data={current} />
              </div>
              <div className={styles.column}>
                <Bottleneck data={current} />
                <InProgress stages={current.stages} />
                <OverSla stages={current.stages} />
              </div>
            </div>
            <StageTable data={current} />
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              {current.source === 'LIVE'
                ? 'По журналу событий ядра: время статуса — до следующего перехода, у заявок в работе — до текущего момента.'
                : 'Синтетический массив сервиса интеграций: заранее посчитанные длительности этапов, чтобы показать дашборд на объёме.'}
            </Typography.Text>
          </>
        )}
      </div>
    </div>
  );
}

type DataProps = { data: DashboardData };
type StagesProps = { stages: DashboardStage[] };

// «Время по этапам»: столбцы этапов банка, узкое место — красным с подписью сверху
function StageChart({ data }: DataProps) {
  const [metric, setMetric] = useState<Metric>('median');
  const stages = data.stages.filter((stage) => stage.owner !== 'CLIENT');
  const value = (stage: DashboardStage) => (metric === 'median' ? stage.median_minutes : stage.p90_minutes) ?? 0;
  const max = Math.max(...stages.map(value), 0);

  return (
    <section className={styles.card} aria-labelledby='stage-chart'>
      <div className={styles.cardHeading}>
        <Typography.Title id='stage-chart' tag='h2' view='xsmall' font='system' color='primary'>
          Время по этапам
        </Typography.Title>
        <div className={styles.toggle} role='group' aria-label='Показатель'>
          {([['median', 'Обычно'], ['p90', '90 % быстрее']] as const).map(([id, title]) => (
            <button key={id} type='button' className={id === metric ? `${styles.toggleItem} ${styles.toggleActive}` : styles.toggleItem}
              aria-pressed={id === metric} onClick={() => setMetric(id)}>
              <Typography.Text view='primary-small' weight='medium' color={id === metric ? 'primary' : 'secondary'}>
                {title}
              </Typography.Text>
            </button>
          ))}
        </div>
      </div>
      {max === 0 ? (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Заявок, прошедших этапы банка, пока нет.
        </Typography.Text>
      ) : (
        <div className={styles.chart} role='list' aria-label='Длительность этапов'>
          <div className={styles.scale} aria-hidden='true'>
            {[max, max / 2, 0].map((tick) => (
              <Typography.Text key={tick} view='secondary-medium' color='secondary'>{tick ? formatTick(tick) : '0'}</Typography.Text>
            ))}
          </div>
          <div className={styles.plot}>
            {stages.map((stage) => {
              const share = (100 * value(stage)) / max;
              const peak = stage.code === data.bottleneck;
              return (
                <div key={stage.code} className={styles.stageColumn} role='listitem'
                  aria-label={`${stage.title}: ${formatMinutes(value(stage))}`}>
                  <div className={styles.barArea}>
                    <div className={peak ? `${styles.barValue} ${styles.peak}` : styles.barValue} style={{ height: `${share}%` }}>
                      {peak && (
                        <Typography.Text className={styles.bubble} view='secondary-large' weight='bold' color='static-primary-light'>
                          {formatTick(value(stage))}
                        </Typography.Text>
                      )}
                    </div>
                  </div>
                  <Typography.Text className={styles.barLabel} view='secondary-medium'
                    color={peak ? 'primary' : 'secondary'} weight={peak ? 'bold' : 'regular'}>
                    {stage.title}
                  </Typography.Text>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

// «Заявки по статусам»: кольцевая диаграмма и легенда
function StatusDonut({ data }: DataProps) {
  const total = data.by_status.reduce((sum, item) => sum + item.count, 0);
  const radius = 15.915; // длина окружности ≈ 100, доли задаются в процентах
  let offset = 25;

  return (
    <section className={styles.card} aria-labelledby='status-donut'>
      <Typography.Title id='status-donut' tag='h2' view='xsmall' font='system' color='primary'>
        Заявки по статусам
      </Typography.Title>
      <div className={styles.donutRow}>
        <div className={styles.donut}>
          <svg viewBox='0 0 42 42' role='img' aria-label={`Всего заявок: ${data.applications}`}>
            <circle cx='21' cy='21' r={radius} fill='none' className={styles.donutTrack} strokeWidth='4' />
            {total > 0 && data.by_status.map((item, index) => {
              const share = (100 * item.count) / total;
              const segment = (
                <circle key={item.code} cx='21' cy='21' r={radius} fill='none' strokeWidth='4'
                  stroke={PALETTE[index % PALETTE.length]} strokeDasharray={`${share} ${100 - share}`} strokeDashoffset={offset} />
              );
              offset -= share;
              return segment;
            })}
          </svg>
          <div className={styles.donutCenter}>
            <Typography.Text view='primary-small' color='secondary'>Всего</Typography.Text>
            <Typography.Title tag='div' view='small' font='system' color='primary'>{data.applications}</Typography.Title>
          </div>
        </div>
        <ul className={styles.legend}>
          {data.by_status.map((item, index) => (
            <li key={item.code}>
              <span className={styles.legendDot} style={{ background: PALETTE[index % PALETTE.length] }} aria-hidden='true' />
              <span>
                <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>{item.title}</Typography.Text>
                <Typography.Text view='primary-medium' weight='bold' color='primary'>
                  {item.count}
                  {total > 0 && <Typography.Text view='primary-small' color='secondary'> · {Math.round((100 * item.count) / total)} %</Typography.Text>}
                </Typography.Text>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

// «Узкое место»: красная карточка с этапом, где заявки ждут дольше всего
function Bottleneck({ data }: DataProps) {
  const stage = data.stages.find((item) => item.code === data.bottleneck);
  return (
    <section className={stage ? `${styles.card} ${styles.alert}` : styles.card} aria-labelledby='bottleneck'>
      <Typography.Text id='bottleneck' view='primary-small' weight='medium' color={stage ? 'static-primary-light' : 'secondary'}>
        {stage ? 'Узкое место' : 'Узких мест не видно'}
      </Typography.Text>
      {stage ? (
        <>
          <Typography.Title tag='div' view='small' font='system' color='static-primary-light'>{stage.title}</Typography.Title>
          <Typography.Text view='primary-small' color='static-primary-light' tag='p' defaultMargins={false}>
            {data.bottleneck_text}
          </Typography.Text>
        </>
      ) : (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Заявок, прошедших этапы банка, пока нет.
        </Typography.Text>
      )}
    </section>
  );
}

// «Сейчас в работе»: сколько заявок на этапе и сколько ждёт самая долгая
function InProgress({ stages }: StagesProps) {
  const active = stages.filter((stage) => stage.in_progress > 0);
  return (
    <section className={styles.card} aria-labelledby='in-progress'>
      <Typography.Title id='in-progress' tag='h2' view='xsmall' font='system' color='primary'>
        Сейчас в работе
      </Typography.Title>
      {active.length === 0 ? (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>Заявок на этапах нет.</Typography.Text>
      ) : (
        <ul className={styles.list}>
          {active.map((stage) => (
            <li key={stage.code} className={styles.listItem}>
              <span className={styles.badge} aria-hidden='true'>
                <Typography.Text view='primary-small' weight='bold' color='primary'>{stage.title[0]}</Typography.Text>
              </span>
              <span className={styles.listText}>
                <Typography.Text view='primary-small' weight='medium' color='primary' tag='p' defaultMargins={false}>{stage.title}</Typography.Text>
                <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
                  дольше всех {formatMinutes(stage.longest_wait_minutes)} · {OWNER[stage.owner]}
                </Typography.Text>
              </span>
              <Typography.Text view='primary-medium' weight='bold' color='primary'>{stage.in_progress}</Typography.Text>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// «Вне срока»: заявки, которые ждут дольше обещанного клиенту срока
function OverSla({ stages }: StagesProps) {
  const late = stages.filter((stage) => stage.over_sla > 0);
  const total = late.reduce((sum, stage) => sum + stage.over_sla, 0);
  return (
    <section className={styles.card} aria-labelledby='over-sla'>
      <div className={styles.cardHeading}>
        <Typography.Title id='over-sla' tag='h2' view='xsmall' font='system' color='primary'>Вне срока</Typography.Title>
        <span className={total > 0 ? `${styles.pill} ${styles.pillAlert}` : styles.pill}>
          <Typography.Text view='primary-medium' weight='bold' color={total > 0 ? 'static-primary-light' : 'primary'}>{total}</Typography.Text>
        </span>
      </div>
      {late.length === 0 ? (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Все заявки укладываются в обещанные сроки.
        </Typography.Text>
      ) : (
        <ul className={styles.list}>
          {late.map((stage) => (
            <li key={stage.code} className={styles.listItem}>
              <span className={styles.listText}>
                <Typography.Text view='primary-small' weight='medium' color='primary' tag='p' defaultMargins={false}>{stage.title}</Typography.Text>
                {stage.sla && <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>срок {stage.sla}</Typography.Text>}
              </span>
              <Typography.Text view='primary-medium' weight='bold' color='primary'>{stage.over_sla}</Typography.Text>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// «Все этапы»: полная таблица показателей
function StageTable({ data }: DataProps) {
  const maxTotal = Math.max(1, ...data.stages.filter((stage) => stage.owner !== 'CLIENT').map((stage) => stage.total_minutes));
  const columns = ['Этап', 'Кто отвечает', 'Прошли', 'Обычно', '90 % быстрее', 'Сейчас', 'Вне срока', 'Доля времени банка'];

  return (
    <section className={styles.card} aria-labelledby='all-stages'>
      <Typography.Title id='all-stages' tag='h2' view='xsmall' font='system' color='primary'>Все этапы</Typography.Title>
      <div className={styles.table} role='table' aria-labelledby='all-stages'>
        <div className={`${styles.tableRow} ${styles.tableHead}`} role='row'>
          {columns.map((title, index) => (
            <Typography.Text key={title} role='columnheader' view='primary-small' color='secondary'
              className={index >= 2 && index <= 6 ? styles.number : undefined}>
              {title}
            </Typography.Text>
          ))}
        </div>
        {data.stages.map((stage) => (
          <div key={stage.code} role='row'
            className={stage.code === data.bottleneck ? `${styles.tableRow} ${styles.peakRow}` : styles.tableRow}>
            <span role='cell'>
              <Typography.Text view='primary-small' weight='bold' color='primary' tag='p' defaultMargins={false}>{stage.title}</Typography.Text>
              {stage.sla && (
                <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>Срок: {stage.sla}</Typography.Text>
              )}
            </span>
            <Cell>{OWNER[stage.owner]}</Cell>
            <Cell number>{stage.passed}</Cell>
            <Cell number>{formatMinutes(stage.median_minutes)}</Cell>
            <Cell number>{formatMinutes(stage.p90_minutes)}</Cell>
            <Cell number>
              {stage.in_progress > 0 ? `${stage.in_progress}, дольше всех ${formatMinutes(stage.longest_wait_minutes)}` : '—'}
            </Cell>
            <Cell number>{stage.over_sla > 0 ? <span className={styles.lateCount}>{stage.over_sla}</span> : '—'}</Cell>
            <span role='cell'>
              {stage.owner === 'CLIENT' ? (
                <Typography.Text view='primary-small' color='secondary'>ждём клиента</Typography.Text>
              ) : (
                <div className={styles.share} aria-label={`${Math.round((100 * stage.total_minutes) / maxTotal)} % от самого долгого этапа`}>
                  <span style={{ width: `${(100 * stage.total_minutes) / maxTotal}%` }} />
                </div>
              )}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Cell({ children, number = false }: { children: ReactNode; number?: boolean }) {
  return (
    <Typography.Text role='cell' view='primary-small' color='primary' className={number ? styles.number : undefined}>
      {children}
    </Typography.Text>
  );
}
