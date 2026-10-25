import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import type { Product } from '../../api/types';
import alfaMark from '../../assets/alfa-mark.svg';
import { formatRub } from '../../format';
import { PrecheckPanel } from './PrecheckPanel';
import styles from './ProductCard.module.css';

type ProductCardProps = {
  product: Product;
  loading: boolean;
  disabled: boolean;
  onApply: () => void;
};

/** Каталог использует ту же белую поверхность и фирменный акцент, что и обзор. */
export function ProductCard({ product, loading, disabled, onApply }: ProductCardProps) {
  const [precheck, setPrecheck] = useState(false);
  return (
    <article className={styles.card} aria-label={product.name}>
      <div className={styles.intro}>
        <span className={styles.brand} aria-hidden='true'><img src={alfaMark} alt='' /></span>
        <Typography.Title tag='h2' view='xsmall' font='system'>{product.name}</Typography.Title>
        <Typography.Text className={styles.description} view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          {product.description}
        </Typography.Text>
      </div>
      <div className={styles.limit}>
        <Typography.Text view='primary-small' color='secondary'>Сумма кредита — до</Typography.Text>
        <Typography.Title className={styles.amount} tag='div' view='medium' font='system'>{formatRub(product.max_amount)}</Typography.Title>
        <Typography.Text view='primary-small' color='secondary'>от {formatRub(product.min_amount)}</Typography.Text>
      </div>
      <dl className={styles.terms}>
        <div>
          <dt><Typography.Text view='primary-small' color='secondary'>Ставка</Typography.Text></dt>
          <dd><Typography.Text view='primary-medium' weight='bold'>от {product.base_rate}% годовых</Typography.Text></dd>
        </div>
        <div>
          <dt><Typography.Text view='primary-small' color='secondary'>Срок</Typography.Text></dt>
          <dd><Typography.Text view='primary-medium' weight='bold'>{product.min_term_months}–{product.max_term_months} мес.</Typography.Text></dd>
        </div>
      </dl>
      {precheck ? (
        <PrecheckPanel product={product} />
      ) : (
        <Button view='transparent' size={40} block={true} onClick={() => setPrecheck(true)}>
          Узнать шансы и сумму по ИНН
        </Button>
      )}
      <Button view='accent' size={48} block={true} loading={loading} disabled={disabled}
        onClick={onApply} aria-label={`Оформить заявку: ${product.name}`}>Оформить заявку</Button>
      <Typography.Text className={styles.note} view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
        Окончательные условия — после решения банка
      </Typography.Text>
    </article>
  );
}
