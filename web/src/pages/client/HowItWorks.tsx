import type { ReactNode } from 'react';
import { Typography } from '@alfalab/core-components/typography';

import { useUser } from '../../auth/AuthContext';
import { StageBar } from '../../components/StageBar';
import styles from './HowItWorks.module.css';

// «Как получить кредит»: четыре шага с маленькими иллюстрациями из интерфейса кабинета
export function HowItWorks() {
  const user = useUser();
  const inn = user.company?.inn ?? '7701234567';

  return (
    <section className={styles.section} aria-labelledby='how-it-works'>
      <Typography.TitleResponsive id='how-it-works' tag='h2' view='medium' font='system'>
        Как получить кредит
      </Typography.TitleResponsive>
      <ol className={styles.steps}>
        <Step title='1. Заполните заявку' caption='онлайн за 5 минут'>
          <div className={styles.picture}>
            <div className={styles.field}>
              <Typography.Text view='secondary-small' color='secondary'>ИНН компании</Typography.Text>
              <Typography.Text view='primary-small' weight='bold'>{inn}</Typography.Text>
            </div>
            <Typography.Text view='secondary-small' color='secondary'>Данные подтянем из ЕГРЮЛ</Typography.Text>
          </div>
        </Step>
        <Step title='2. Проверка и оценка' caption='обычно 2–4 минуты'>
          <div className={styles.picture}>
            <StageBar status='SCORING' />
            <Typography.Text view='secondary-medium'>Проверка данных</Typography.Text>
          </div>
        </Step>
        <Step title='3. Решение банка' caption='до 2 часов в рабочее время'>
          <div className={styles.toast}>
            <Typography.Text view='secondary-medium' color='primary-inverted'>Заявка одобрена</Typography.Text>
            <Typography.Text view='secondary-medium' color='primary-inverted' className={styles.underline}>Открыть</Typography.Text>
          </div>
        </Step>
        <Step title='4. Подписание и деньги' caption='подпись кодом, зачисление до 15 минут'>
          <div className={`${styles.picture} ${styles.code}`} aria-hidden='true'>
            {['4', '8', '2', '', '', ''].map((digit, index) => (
              <span key={index} className={index === 3 ? `${styles.cell} ${styles.focus}` : styles.cell}>
                <Typography.Text view='primary-small' weight='bold'>{digit}</Typography.Text>
              </span>
            ))}
          </div>
        </Step>
      </ol>
    </section>
  );
}

type StepProps = {
  title: string;
  caption: string;
  children: ReactNode;
};

function Step({ title, caption, children }: StepProps) {
  return (
    <li className={styles.step}>
      <Typography.Title tag='h3' view='small' font='system'>{title}</Typography.Title>
      <Typography.Text view='primary-small' color='secondary'>{caption}</Typography.Text>
      <div className={styles.illustration}>{children}</div>
    </li>
  );
}
