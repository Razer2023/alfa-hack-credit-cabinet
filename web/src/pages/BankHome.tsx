import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Status } from '@alfalab/core-components/status';
import { Typography } from '@alfalab/core-components/typography';

// Заглушка рабочего места банка: очередь заявок и карточка андеррайтера появятся по ТЗ tz/D-web/2026-10-21-a-core-api.md.
export function BankHome() {
  return (
    <>
      <Gap size={24} />
      <Typography.Title tag='h1' view='medium' font='system'>
        Рабочее место банка
      </Typography.Title>
      <Gap size={8} />
      <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
        Очередь заявок для менеджера и карточка андеррайтера.
      </Typography.Text>
      <Gap size={24} />

      <Plate view='common' rounded={true} border={true} title='Очередь заявок'>
        <Status view='muted-alt' color='orange'>
          У специалиста
        </Status>
        <Gap size={8} />
        Здесь появится таблица заявок с фильтрами по статусу.
      </Plate>
    </>
  );
}
