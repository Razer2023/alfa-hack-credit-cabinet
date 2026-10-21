import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Status } from '@alfalab/core-components/status';
import { Typography } from '@alfalab/core-components/typography';

// Заглушка кабинета клиента: каталог, мастер заявки и трекер появятся по ТЗ tz/D-web/2026-10-21-a-core-api.md.
export function ClientHome() {
  return (
    <>
      <Gap size={24} />
      <Typography.Title tag='h1' view='medium' font='system'>
        Кабинет клиента
      </Typography.Title>
      <Gap size={8} />
      <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
        Выберите кредит, заполните заявку и следите за её статусом.
      </Typography.Text>
      <Gap size={24} />

      <Plate
        view='common'
        rounded={true}
        border={true}
        title='Каталог продуктов'
        buttons={[
          <Button key='apply' view='accent' size={40} disabled={true}>
            Оформить
          </Button>,
        ]}
      >
        <Status view='muted-alt' color='blue'>
          Скоро
        </Status>
        <Gap size={8} />
        Здесь появятся кредитные продукты с суммами, сроками и ставками.
      </Plate>
    </>
  );
}
