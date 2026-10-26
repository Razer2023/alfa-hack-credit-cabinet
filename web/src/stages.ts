import type { Application, ApplicationStatus } from './api/types';

// Путь заявки для клиента (S4.5). Каждый этап завершается одним из статусов.
export const STAGES: { title: string; reachedBy: ApplicationStatus[] }[] = [
  { title: 'Заявка отправлена', reachedBy: ['SUBMITTED'] },
  { title: 'Проверка данных', reachedBy: ['SCORING'] },
  { title: 'Оценка заявки', reachedBy: ['PENDING_APPROVAL', 'MANUAL_REVIEW', 'REJECTED'] },
  { title: 'Решение банка', reachedBy: ['APPROVED', 'COUNTER_OFFER', 'REJECTED'] },
  { title: 'Подписание договора', reachedBy: ['SIGNED'] },
  { title: 'Деньги зачислены', reachedBy: ['ISSUED'] },
];

// Номер этапа (с 1), на котором заявка сейчас
export const CURRENT_STAGE: Record<ApplicationStatus, number> = {
  DRAFT: 1,
  SUBMITTED: 2,
  CHECKING: 2,
  NEED_INFO: 2,
  SCORING: 3,
  PENDING_APPROVAL: 4,
  MANUAL_REVIEW: 4,
  COUNTER_OFFER: 5,
  APPROVED: 5,
  REJECTED: 4,
  SIGNED: 6,
  ISSUED: 6,
  CANCELLED: 1,
};

const WAITING: ApplicationStatus[] = ['SUBMITTED', 'CHECKING', 'SCORING', 'PENDING_APPROVAL', 'MANUAL_REVIEW'];

// Следующий шаг клиента — из доступных действий (allowed_actions) и статуса заявки
export function nextStep(application: Application): string {
  const actions = application.allowed_actions;
  if (actions.includes('EDIT')) return 'Продолжите заполнение заявки';
  if (actions.includes('PROVIDE_INFO')) return 'Банку нужны дополнительные данные';
  if (actions.includes('ACCEPT_OFFER')) return 'Проверьте предложенные условия';
  if (actions.includes('SIGN')) return 'Следующий шаг — подписание';
  if (WAITING.includes(application.status.code)) return 'Следующий шаг — решение банка';
  return application.status.title;
}

// «Этап 4 из 6 · Решение банка»
export function stageLabel(status: ApplicationStatus): string {
  if (status === 'ISSUED') return `Все ${STAGES.length} этапов пройдены`;
  if (status === 'CANCELLED') return 'Заявка отменена';
  const current = CURRENT_STAGE[status];
  return `Этап ${current} из ${STAGES.length} · ${STAGES[current - 1].title}`;
}
