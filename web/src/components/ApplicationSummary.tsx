import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import type { Application } from '../api/types';
import alfaMark from '../assets/alfa-mark.svg';
import { formatRub } from '../format';
import styles from './ApplicationSummary.module.css';

type ApplicationSummaryProps = {
  application: Application;
  productName: string;
  onOpen?: () => void;
};

/** Общая карточка: параметры запроса и следующий шаг из актуального состояния API. */
export function ApplicationSummary({ application, productName, onOpen }: ApplicationSummaryProps) {
  const actions = application.allowed_actions;
  const waiting = ['SUBMITTED', 'CHECKING', 'SCORING', 'PENDING_APPROVAL', 'MANUAL_REVIEW'].includes(application.status.code);
  const next = actions.includes('EDIT') ? 'Продолжите заполнение заявки'
    : actions.includes('PROVIDE_INFO') ? 'Банку нужны дополнительные данные'
    : actions.includes('ACCEPT_OFFER') ? 'Проверьте предложенные условия'
    : actions.includes('SIGN') ? 'Следующий шаг — подписание'
    : waiting ? 'Следующий шаг — решение банка' : application.status.title;

  return (
    <section className={styles.card} aria-label={`Заявка ${application.number}`}>
      <div className={styles.hero}>
        <img className={styles.watermark} src={alfaMark} alt='' aria-hidden='true' />
        <div className={styles.top}>
          <Typography.Text view='primary-small' color='static-primary-light'>
            {application.number} · {productName}
          </Typography.Text>
          <Typography.Text className={styles.status} view='secondary-large' color='static-primary-light'>
            {application.status.title}
          </Typography.Text>
        </div>
        <Typography.Title className={styles.amount} tag='div' view='xlarge' font='system' color='static-primary-light'>
          {application.amount !== null ? formatRub(application.amount) : 'Сумма не указана'}
        </Typography.Title>
        <Typography.Text view='primary-small' color='static-primary-light' tag='p' defaultMargins={false}>
          {application.purpose || 'Цель пока не указана'}
          {application.term_months !== null && ` · ${application.term_months} мес.`}
        </Typography.Text>
        <Typography.Text className={styles.caption} view='secondary-large' color='static-primary-light' tag='p' defaultMargins={false}>
          Запрошенная сумма и срок
        </Typography.Text>
      </div>
      <div className={styles.next}>
        <div className={styles.explanation}>
          <Typography.Text view='primary-medium' weight='bold' tag='div'>{next}</Typography.Text>
          <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
            {application.status.hint}
          </Typography.Text>
        </div>
        {onOpen && <Button view='secondary' size={48} onClick={onOpen}>
          {actions.includes('EDIT') ? 'Продолжить' : 'Открыть заявку'}
        </Button>}
      </div>
    </section>
  );
}
