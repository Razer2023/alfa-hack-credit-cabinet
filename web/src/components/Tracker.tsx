import { Steps } from '@alfalab/core-components/steps';
import { Typography } from '@alfalab/core-components/typography';

import type { ApplicationEvent, ApplicationStatus } from '../api/types';
import { formatDateTime } from '../format';

// Путь заявки для клиента (S4.5). Каждый этап завершается одним из статусов.
const STAGES: { title: string; reachedBy: ApplicationStatus[] }[] = [
  { title: 'Заявка отправлена', reachedBy: ['SUBMITTED'] },
  { title: 'Проверка данных', reachedBy: ['SCORING'] },
  { title: 'Оценка заявки', reachedBy: ['PENDING_APPROVAL', 'MANUAL_REVIEW', 'REJECTED'] },
  { title: 'Решение банка', reachedBy: ['APPROVED', 'COUNTER_OFFER', 'REJECTED'] },
  { title: 'Подписание договора', reachedBy: ['SIGNED'] },
  { title: 'Деньги зачислены', reachedBy: ['ISSUED'] },
];

// Номер этапа (с 1), на котором заявка сейчас
const CURRENT_STAGE: Record<ApplicationStatus, number> = {
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

type TrackerProps = {
  status: ApplicationStatus;
  events: ApplicationEvent[];
};

export function Tracker({ status, events }: TrackerProps) {
  const current = CURRENT_STAGE[status];
  const reachedAt = (stage: (typeof STAGES)[number]) =>
    events.find((event) => event.to_status && stage.reachedBy.includes(event.to_status))?.created_at;

  return (
    <Steps
      isVerticalAlign={true}
      ordered={true}
      interactive={false}
      activeStep={current}
      checkIsStepWarning={(step) => status === 'NEED_INFO' && step === current}
      checkIsStepWaiting={(step) => (status === 'MANUAL_REVIEW' || status === 'PENDING_APPROVAL') && step === current}
      checkIsStepError={(step) => status === 'REJECTED' && step === current}
      checkIsStepPositive={(step) => status === 'ISSUED' && step === current}
    >
      {STAGES.map((stage) => {
        const at = reachedAt(stage);
        return (
          <div key={stage.title}>
            <Typography.Text view='primary-medium'>{stage.title}</Typography.Text>
            {at && (
              <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                {formatDateTime(at)}
              </Typography.Text>
            )}
          </div>
        );
      })}
    </Steps>
  );
}
