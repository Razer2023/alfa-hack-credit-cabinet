import type { StatusProps } from '@alfalab/core-components/status';

import type { ApplicationStatus, DataSource } from './api/types';

const rubles = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const dateTime = new Intl.DateTimeFormat('ru-RU', {
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
});

export function formatRub(value: number): string {
  return `${rubles.format(value)} ₽`;
}

export function formatDateTime(value: string): string {
  return dateTime.format(new Date(value));
}

const time = new Intl.DateTimeFormat('ru-RU', { hour: '2-digit', minute: '2-digit' });

export function formatTime(value: string): string {
  return time.format(new Date(value));
}

export function formatMonths(value: number): string {
  const rest10 = value % 10;
  const rest100 = value % 100;
  if (rest10 === 1 && rest100 !== 11) return `${value} месяц`;
  if (rest10 >= 2 && rest10 <= 4 && (rest100 < 12 || rest100 > 14)) return `${value} месяца`;
  return `${value} месяцев`;
}

export const STATUS_COLOR: Record<ApplicationStatus, NonNullable<StatusProps['color']>> = {
  DRAFT: 'grey',
  SUBMITTED: 'blue',
  CHECKING: 'blue',
  NEED_INFO: 'orange',
  SCORING: 'blue',
  PENDING_APPROVAL: 'blue',
  MANUAL_REVIEW: 'purple',
  APPROVED: 'green',
  COUNTER_OFFER: 'teal',
  REJECTED: 'red',
  SIGNED: 'green',
  ISSUED: 'green',
  CANCELLED: 'grey',
};

export const SOURCE_LABEL: Record<DataSource, string> = {
  EGRUL: 'ЕГРЮЛ',
  FNS: 'ФНС',
  BANK_ACCOUNT: 'Выписка',
};

// Поля профиля компании от сервиса B. Неизвестные поля показываются под своим ключом.
export const COMPANY_FIELDS: Record<string, string> = {
  name: 'Название',
  ogrn: 'ОГРН',
  registration_date: 'Дата регистрации',
  okved: 'ОКВЭД',
  address: 'Адрес',
  director: 'Руководитель',
  employees: 'Сотрудников',
  tax_regime: 'Налоговый режим',
  revenue_year: 'Выручка за год',
  avg_monthly_turnover: 'Средний оборот в месяц',
};

const MONEY_FIELDS = new Set(['revenue_year', 'avg_monthly_turnover']);

export function formatCompanyValue(field: string, value: string | number | boolean): string {
  if (MONEY_FIELDS.has(field) && typeof value === 'number') return formatRub(value);
  if (typeof value === 'boolean') return value ? 'да' : 'нет';
  return String(value);
}
