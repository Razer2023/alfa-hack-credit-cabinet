import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { PaymentCalc, Product } from '../../api/types';
import { type LoanTerms, termsError } from './loanTerms';

// Расчёт платежа по сумме и сроку (S3.2), с задержкой ~300 мс после ввода. enabled = false — без запросов.
export function usePayment(product: Product | undefined, terms: LoanTerms, enabled = true): PaymentCalc | null {
  const errors = termsError(product, terms);
  const term = Number(terms.term);
  const calcKey =
    enabled && product && terms.amount && term > 0 && !errors.amount && !errors.term
      ? `${product.code}:${terms.amount}:${term}`
      : null;
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

  return calc && calc.key === calcKey ? calc.value : null;
}
