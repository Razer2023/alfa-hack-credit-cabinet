import { Status } from '@alfalab/core-components/status';

import type { StatusOut } from '../api/types';
import { STATUS_COLOR } from '../format';

type StatusLabelProps = {
  status: StatusOut;
};

// Название статуса приходит из API (status.title), здесь только цвет
export function StatusLabel({ status }: StatusLabelProps) {
  return (
    <Status view='soft' color={STATUS_COLOR[status.code]}>
      {status.title}
    </Status>
  );
}
