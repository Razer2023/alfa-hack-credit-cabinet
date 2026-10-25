import { useEffect, useState } from 'react';
import { AmountInput } from '@alfalab/core-components/amount-input';
import { Input } from '@alfalab/core-components/input';
import { Typography } from '@alfalab/core-components/typography';

import { api } from '../../api/client';
import type { PaymentCalc, Product } from '../../api/types';
import { Money } from '../../components/Money';
import { Term } from '../../components/Term';
import { formatRub } from '../../format';
import { type LoanTerms, termsError } from './loanTerms';
import styles from './Forms.module.css';

type LoanFieldsProps = {
  product: Product | undefined;
  terms: LoanTerms;
  onChange: (terms: LoanTerms) => void;
};

// Сумма, срок, цель и расчёт платежа (S3.2)
export function LoanFields({ product, terms, onChange }: LoanFieldsProps) {
  const errors = termsError(product, terms);
  const term = Number(terms.term);
  const calcKey =
    product && terms.amount && term > 0 && !errors.amount && !errors.term ? `${product.code}:${terms.amount}:${term}` : null;
  const [calc, setCalc] = useState<{ key: string; value: PaymentCalc } | null>(null);

  useEffect(() => {
    if (!calcKey || !product || !terms.amount) return;
    const body = { product_code: product.code, amount: terms.amount, term_months: term };
    const timer = setTimeout(() => {
      api<PaymentCalc>('/calc/payment', { method: 'POST', body })
        .then((value) => setCalc({ key: calcKey, value }))
        .catch(() => setCalc(null));
    }, 300);
    return () => clearTimeout(timer);
  }, [calcKey, product, terms.amount, term]);

  const payment = calc && calc.key === calcKey ? calc.value : null;

  return (
    <>
      <div className={styles.fields}>
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
          hint={product && !errors.term ? `от ${product.min_term_months} до ${product.max_term_months}` : undefined}
          onChange={(_, { value }) => onChange({ ...terms, term: value.replace(/\D/g, '') })}
        />
        <Input
          label='Цель кредита'
          block={true}
          className={styles.wide}
          value={terms.purpose}
          maxLength={500}
          onChange={(_, { value }) => onChange({ ...terms, purpose: value })}
        />
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
