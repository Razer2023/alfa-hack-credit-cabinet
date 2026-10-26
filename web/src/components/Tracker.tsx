import { Steps } from '@alfalab/core-components/steps';
import { Typography } from '@alfalab/core-components/typography';

import type { ApplicationEvent, ApplicationStatus } from '../api/types';
import { formatDateTime } from '../format';
import { CURRENT_STAGE, STAGES } from '../stages';

type TrackerProps = {
  status: ApplicationStatus;
  events: ApplicationEvent[];
  sla?: string | null;
};

export function Tracker({ status, events, sla }: TrackerProps) {
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
      {STAGES.map((stage, index) => {
        const at = reachedAt(stage);
        const inProgress = index + 1 === current && sla;
        return (
          <div key={stage.title}>
            <Typography.Text view='primary-medium'>{stage.title}</Typography.Text>
            {inProgress && (
              <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                обычно {sla}
              </Typography.Text>
            )}
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
