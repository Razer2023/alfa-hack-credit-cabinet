import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Typography } from '@alfalab/core-components/typography';

import type { Application } from '../../api/types';
import styles from './Forms.module.css';

// Что клиенту делать дальше по каждой причине отказа (S6.3). Коды и тексты причин — из скоринга (services/scoring/rules)
const ADVICE: Record<string, string> = {
  EGRUL_INACTIVE: 'Проверьте сведения о компании в ЕГРЮЛ. Когда статус обновится, заявку можно подать снова.',
  BUSINESS_TOO_YOUNG: 'Вернитесь, когда бизнесу исполнится 6 месяцев — обороты по счёту за это время помогут одобрению.',
  BKI_OVERDUE_CRITICAL:
    'Погасите просрочку и дождитесь обновления кредитной истории — обычно до 10 рабочих дней, затем подайте заявку.',
  LOW_SCORE: 'Попробуйте меньшую сумму или более длинный срок — шансы можно оценить заранее, без заявки.',
  CANNOT_AFFORD_MIN: 'Банку нужны большие обороты по расчётному счёту. Подойти может другой продукт с меньшей суммой.',
  BELOW_PRODUCT_MIN: 'Выберите продукт с меньшей минимальной суммой.',
  AMOUNT_OVER_PRODUCT: 'Уменьшите сумму или выберите продукт с большим лимитом.',
};
const STAFF_ADVICE = 'Обсудите решение с менеджером — он подскажет, что можно изменить в заявке.';

type RejectionBlockProps = {
  application: Application;
};

// Понятная причина отказа: почему и что делать дальше (S6.3)
export function RejectionBlock({ application }: RejectionBlockProps) {
  const decision = application.decision;
  const reasons = decision?.reasons ?? [];
  const byStaff = decision?.decided_by !== 'SYSTEM';

  return (
    <Plate view='negative' rounded={true} border={true} title='Банк не может одобрить заявку сейчас'>
      <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
        Почему
      </Typography.Text>
      {reasons.length === 0 && (
        <Typography.Text view='primary-medium' tag='p' defaultMargins={false}>
          Заявка не прошла кредитную политику банка.
        </Typography.Text>
      )}
      {reasons.map((reason) => (
        <div key={reason.code} className={styles.reason}>
          <Typography.Text view='primary-medium' tag='p' defaultMargins={false}>
            {reason.text}
          </Typography.Text>
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            Что можно сделать: {ADVICE[reason.code] ?? STAFF_ADVICE}
          </Typography.Text>
        </div>
      ))}
      <Gap size={16} />
      <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
        Что дальше
      </Typography.Text>
      <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
        {byStaff
          ? 'Решение принял кредитный специалист. Менеджер расскажет подробности — контакты рядом.'
          : 'Решение принято автоматически по кредитной политике. Если остались вопросы — напишите менеджеру, контакты рядом.'}
      </Typography.Text>
      <Gap size={12} />
      <Button view='secondary' size={40} href='#/products'>
        Оценить шансы на другую сумму
      </Button>
    </Plate>
  );
}
