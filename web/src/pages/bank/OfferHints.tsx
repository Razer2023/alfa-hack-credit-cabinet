import { Button } from '@alfalab/core-components/button';
import { Plate } from '@alfalab/core-components/plate';
import { Status } from '@alfalab/core-components/status';
import { Typography } from '@alfalab/core-components/typography';

import type { OfferCheck } from '../../api/types';
import { formatRub } from '../../format';
import styles from './Bank.module.css';

type OfferHintsProps = {
  check: OfferCheck;
  onApplySuggestion: (terms: { amount: number; term_months: number; rate: number | null }) => void;
};

// Подсказки скоринга, пока сотрудник вводит условия (S5.4): потянет ли компания платёж
export function OfferHints({ check, onApplySuggestion }: OfferHintsProps) {
  const checks = check.checks ?? [];
  const errors = checks.filter((item) => item.level === 'error');
  const warnings = checks.filter((item) => item.level === 'warning');
  const dscr = check.metrics?.dscr;
  const suggestion = check.suggestion;

  return (
    <div className={styles.hints} aria-live='polite'>
      {check.allowed && errors.length === 0 && warnings.length === 0 && (
        <div className={styles.hintOk}>
          <Status view='soft' color='green' size={20}>
            Условия в рамках политики банка
          </Status>
          <Typography.Text view='primary-small' color='secondary'>
            {check.monthly_payment != null && `Платёж ${formatRub(check.monthly_payment)}`}
            {dscr != null && ` · DSCR ${dscr}`}
          </Typography.Text>
        </div>
      )}
      {errors.length > 0 && (
        <Plate view='negative' rounded={true} title='Условия не проходят политику банка'>
          {errors.map((item) => (
            <Typography.Text key={item.code} view='primary-small' tag='p' defaultMargins={false}>
              {item.text}
            </Typography.Text>
          ))}
        </Plate>
      )}
      {warnings.length > 0 && (
        <Plate view='attention' rounded={true} title='Обратите внимание'>
          {warnings.map((item) => (
            <Typography.Text key={item.code} view='primary-small' tag='p' defaultMargins={false}>
              {item.text}
            </Typography.Text>
          ))}
        </Plate>
      )}
      {suggestion && (
        <Button
          view='secondary'
          size={32}
          onClick={() =>
            onApplySuggestion({ amount: suggestion.amount, term_months: suggestion.term_months, rate: suggestion.rate ?? null })
          }
        >
          Подставить {formatRub(suggestion.amount)}
        </Button>
      )}
    </div>
  );
}
