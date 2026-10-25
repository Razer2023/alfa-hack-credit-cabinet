import { Link } from '@alfalab/core-components/link';
import { Plate } from '@alfalab/core-components/plate';
import { Typography } from '@alfalab/core-components/typography';

import type { Application } from '../api/types';
import { type Fact, FactList } from './FactList';

type ManagerContactProps = {
  manager: NonNullable<Application['manager']>;
};

// Кто ведёт заявку и как с ним связаться (S4.9)
export function ManagerContact({ manager }: ManagerContactProps) {
  const facts: Fact[] = [];
  if (manager.phone) {
    const tel = manager.phone.replace(/[^\d+]/g, '');
    facts.push({ label: 'Телефон', value: <Link href={`tel:${tel}`}>{manager.phone}</Link> });
  }
  if (manager.work_hours) facts.push({ label: 'Часы работы', value: manager.work_hours });

  return (
    <Plate view='common' rounded={true} border={true} title='Ваш менеджер'>
      <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
        {manager.full_name}
      </Typography.Text>
      {manager.position && (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          {manager.position}
        </Typography.Text>
      )}
      {facts.length > 0 && <FactList facts={facts} />}
    </Plate>
  );
}
