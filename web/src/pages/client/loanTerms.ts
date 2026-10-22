import type { Product } from '../../api/types';
import { formatRub } from '../../format';

export type LoanTerms = {
  amount: number | null;
  term: string;
  purpose: string;
};

// Подсказки по границам продукта; окончательную проверку делает ядро
export function termsError(product: Product | undefined, terms: LoanTerms) {
  const term = Number(terms.term);
  return {
    amount:
      product && terms.amount !== null && (terms.amount < product.min_amount || terms.amount > product.max_amount)
        ? `От ${formatRub(product.min_amount)} до ${formatRub(product.max_amount)}`
        : undefined,
    term:
      product && terms.term && (term < product.min_term_months || term > product.max_term_months)
        ? `От ${product.min_term_months} до ${product.max_term_months} мес.`
        : undefined,
  };
}

export function termsReady(product: Product | undefined, terms: LoanTerms): boolean {
  const errors = termsError(product, terms);
  return Boolean(terms.amount && Number(terms.term) > 0 && terms.purpose.trim() && !errors.amount && !errors.term);
}
