import { AmountInput } from '@alfalab/core-components/amount-input';
import { Input } from '@alfalab/core-components/input';
import { Typography } from '@alfalab/core-components/typography';

import type { Product } from '../../api/types';
import { Money } from '../../components/Money';
import { Term } from '../../components/Term';
import { formatRub } from '../../format';
import { type LoanTerms, termsError } from './loanTerms';
import styles from './Forms.module.css';
import { usePayment } from './usePayment';

type LoanFieldsProps = {
  product: Product | undefined;
  terms: LoanTerms;
  onChange: (terms: LoanTerms) => void;
  // Черновик: группы «Сумма и срок» и «Цель», а платёж показан рядом с формой (DraftForm)
  grouped?: boolean;
};

// Сумма, срок, цель и расчёт платежа (S3.2)
export function LoanFields({ product, terms, onChange, grouped = false }: LoanFieldsProps) {
  const errors = termsError(product, terms);
  const payment = usePayment(product, terms, !grouped);

  const amountAndTerm = (
    <div className={styles.pair}>
      <AmountInput
        label='Сумма кредита'
        block={true}
        currency='RUB'
        integersOnly={true}
        positiveOnly={true}
        value={terms.amount === null ? null : terms.amount * 100}
        error={errors.amount}
        hint={product && !errors.amount ? `от ${formatRub(product.min_amount)} до ${formatRub(product.max_amount)}` : undefined}
        onChange={(_, { value }) => onChange({ ...terms, amount: value === null ? null : Math.round(value / 100) })}
      />
      <Input
        label='Срок, месяцев'
        block={true}
        inputMode='numeric'
        value={terms.term}
        error={errors.term}
        hint={product && !errors.term
          ? `от ${product.min_term_months} до ${product.max_term_months}${grouped ? ' — чем дольше, тем меньше платёж' : ''}`
          : undefined}
        onChange={(_, { value }) => onChange({ ...terms, term: value.replace(/\D/g, '') })}
      />
    </div>
  );
  const purpose = (
    <Input
      label='Цель кредита'
      block={true}
      value={terms.purpose}
      maxLength={500}
      hint={grouped ? 'Своими словами: на что пойдут деньги' : undefined}
      onChange={(_, { value }) => onChange({ ...terms, purpose: value })}
    />
  );

  if (grouped) {
    return (
      <>
        <div className={styles.group}>
          <Typography.Title tag='h3' view='xsmall' font='system'>Сумма и срок</Typography.Title>
          {amountAndTerm}
        </div>
        <div className={styles.group}>
          <Typography.Title tag='h3' view='xsmall' font='system'>Цель</Typography.Title>
          {purpose}
        </div>
      </>
    );
  }

  return (
    <>
      <div className={styles.fields}>
        {amountAndTerm}
        {purpose}
      </div>
      {payment && (
        <div className={styles.payment}>
          <div>
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              <Term>Платёж в месяц</Term>
            </Typography.Text>
            <Typography.Title tag='div' view='small' font='system'>
              <Money value={payment.monthly_payment} bold={true} />
            </Typography.Title>
          </div>
          <div>
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              <Term>Ставка</Term>
            </Typography.Text>
            <Typography.Title tag='div' view='small' font='system'>
              {payment.rate}%
            </Typography.Title>
          </div>
        </div>
      )}
    </>
  );
}
