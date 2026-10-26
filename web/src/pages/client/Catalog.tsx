import { useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, Product, ProductMatch } from '../../api/types';
import { DotLabel } from '../../components/StatusDot';
import { Term } from '../../components/Term';
import { formatRub } from '../../format';
import { Hero, Sheet } from '../../layout/Page';
import { navigate } from '../../router';
import styles from './Catalog.module.css';
import { HowItWorks } from './HowItWorks';
import { PrecheckPanel } from './PrecheckPanel';
import { type MatchRequest, ProductMatcher } from './ProductMatcher';

type MatchResult = { request: MatchRequest; matches: ProductMatch[] };

// Кредиты (S1.1, S1.2, S2.1): подбор по задаче и «Наше предложение», ниже — все продукты
export function Catalog() {
  const [products, setProducts] = useState<Product[]>([]);
  const [match, setMatch] = useState<MatchResult | null>(null);
  // Продукт, который клиент сам выбрал в списке; без выбора в карточке — лучший по подбору
  const [chosen, setChosen] = useState<string | null>(null);
  const [creating, setCreating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Product[]>('/products').then(setProducts).catch((e) => setError(errorMessage(e)));
  }, []);

  const onMatch = useCallback((result: MatchResult | null) => {
    setMatch(result);
    setChosen(null);
  }, []);

  async function apply(product: Product) {
    setCreating(product.code);
    setError(null);
    try {
      const created = await api<Application>('/applications', { method: 'POST', body: { product_code: product.code } });
      // Что клиент указал в подборе, сразу попадает в черновик; сумму и срок — только если они в рамках продукта
      const picked = match?.matches.find((item) => item.product.code === product.code);
      if (match && picked) {
        const body = picked.fits
          ? { purpose: match.request.title, amount: match.request.amount ?? undefined, term_months: match.request.term_months ?? undefined }
          : { purpose: match.request.title };
        await api<Application>(`/applications/${created.id}`, { method: 'PATCH', body });
      }
      navigate(`/applications/${created.id}`);
    } catch (e) {
      setError(errorMessage(e));
      setCreating(null);
    }
  }

  const listed = match ? match.matches.map((item) => item.product) : products;
  const recommended = match?.matches.find((item) => item.recommended)?.product;
  const focus = listed.find((product) => product.code === chosen) ?? recommended ?? listed[0];
  const rates = products.map((product) => product.base_rate);

  return (
    <>
      <Hero className={styles.hero}>
        <Typography.TitleResponsive tag='h1' view='xlarge' font='system' color='primary-inverted'>
          Кредит под вашу задачу
        </Typography.TitleResponsive>
        <Typography.Text view='primary-medium' color='secondary-inverted' tag='p' defaultMargins={false}>
          Сравните суммы, сроки и условия финансирования.
        </Typography.Text>
      </Hero>
      <Sheet className={styles.sheet}>
        {error && <Plate view='negative' rounded={true} title='Не удалось загрузить данные'>{error}</Plate>}
        {products.length === 0 && !error && <Spinner preset={24} visible={true} />}

        {focus && (
          <section className={styles.calculator} aria-labelledby='calculator'>
            <div className={styles.calculatorMain}>
              <Typography.TitleResponsive id='calculator' tag='h2' view='medium' font='system'>
                Рассчитайте условия
              </Typography.TitleResponsive>
              <ProductMatcher onResult={onMatch} />
              {rates.length > 0 && (
                <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
                  Ставка от {Math.min(...rates)}% до {Math.max(...rates)}% годовых зависит от продукта и решения банка.
                  Расчёт предварительный.
                </Typography.Text>
              )}
            </div>
            <OfferPreview
              key={focus.code}
              product={focus}
              match={match?.matches.find((item) => item.product.code === focus.code)}
              loading={creating === focus.code}
              disabled={creating !== null}
              onApply={() => apply(focus)}
            />
          </section>
        )}

        {listed.length > 0 && (
          <section className={styles.products} aria-labelledby='all-products'>
            <Typography.Title id='all-products' tag='h2' view='small' font='system'>Все продукты</Typography.Title>
            <div className={styles.table} role='table' aria-label='Кредитные продукты'>
              <div className={`${styles.productRow} ${styles.tableHead}`} role='row'>
                {['Продукт', 'Сумма до', 'Срок', 'Ставка от', ''].map((title, index) => (
                  <Typography.Text key={index} role='columnheader' view='primary-small' color='secondary'
                    className={index > 0 && index < 4 ? styles.right : undefined}>
                    {title === 'Ставка от' ? <><Term>Ставка</Term> от</> : title}
                  </Typography.Text>
                ))}
              </div>
              {listed.map((product) => {
                const selected = product.code === focus?.code;
                return (
                  <div key={product.code} className={styles.productRow} role='row'>
                    <span className={styles.productName} role='cell'>
                      <Typography.Text view='primary-medium' weight='bold'>{product.name}</Typography.Text>
                      <Typography.Text view='primary-small' color='secondary'>{product.description}</Typography.Text>
                      <Typography.Text className={styles.mobileTerms} view='primary-small' color='secondary'>
                        до {formatRub(product.max_amount)} · {product.min_term_months}–{product.max_term_months} мес. · от {product.base_rate}%
                      </Typography.Text>
                    </span>
                    <Typography.Text className={`${styles.right} ${styles.desktop}`} role='cell' view='primary-medium' weight='bold'>
                      {formatRub(product.max_amount)}
                    </Typography.Text>
                    <Typography.Text className={`${styles.right} ${styles.desktop}`} role='cell' view='primary-medium'>
                      {product.min_term_months}–{product.max_term_months} мес.
                    </Typography.Text>
                    <Typography.Text className={`${styles.right} ${styles.desktop}`} role='cell' view='primary-medium'>
                      {product.base_rate}%
                    </Typography.Text>
                    <span role='cell'>
                      <Button
                        view={selected ? 'primary' : 'secondary'}
                        size={40}
                        block={true}
                        aria-pressed={selected}
                        aria-label={`${product.name}: показать в расчёте`}
                        onClick={() => setChosen(product.code)}
                      >
                        {selected ? 'В расчёте' : 'Выбрать'}
                      </Button>
                    </span>
                  </div>
                );
              })}
            </div>
            <Typography.Text view='secondary-large' color='secondary'>Окончательные условия — после решения банка.</Typography.Text>
          </section>
        )}

        <HowItWorks />
      </Sheet>
    </>
  );
}

type OfferPreviewProps = {
  product: Product;
  match?: ProductMatch;
  loading: boolean;
  disabled: boolean;
  onApply: () => void;
};

// «Наше предложение»: условия выбранного продукта, оформление заявки и предоценка по ИНН (9a, 9b)
function OfferPreview({ product, match, loading, disabled, onApply }: OfferPreviewProps) {
  const [precheck, setPrecheck] = useState(false);

  const applyButton = (
    <Button view='accent' size={56} block={true} loading={loading} disabled={disabled}
      onClick={onApply} aria-label={`Оформить заявку: ${product.name}`}>
      Оформить заявку
    </Button>
  );

  if (precheck) {
    return (
      <aside className={styles.offer} aria-label='Шансы по ИНН'>
        <div className={styles.offerHeading}>
          <Typography.Title tag='h3' view='small' font='system'>Шансы по ИНН</Typography.Title>
          <Button view='text' size={32} onClick={() => setPrecheck(false)}>← К предложению</Button>
        </div>
        <PrecheckPanel product={product} />
        {applyButton}
      </aside>
    );
  }

  return (
    <aside className={styles.offer} aria-label='Наше предложение'>
      <Typography.Title tag='h3' view='small' font='system'>Наше предложение</Typography.Title>
      <div className={styles.offerProduct}>
        <Typography.Text view='primary-medium' weight='medium'>{product.name}</Typography.Text>
        {match?.recommended && <DotLabel tone='positive'>Подходит лучше всего</DotLabel>}
        {(match ? match.notes : [product.description]).map((note) => (
          <Typography.Text key={note} view='primary-small' color='secondary' tag='p' defaultMargins={false}>{note}</Typography.Text>
        ))}
      </div>
      <div>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>Сумма кредита — до</Typography.Text>
        <Typography.Title className={styles.number} tag='div' view='medium' font='system'>{formatRub(product.max_amount)}</Typography.Title>
        <Typography.Text view='primary-small' color='secondary'>от {formatRub(product.min_amount)}</Typography.Text>
      </div>
      <dl className={styles.facts}>
        <div>
          <dt><Typography.Text view='primary-small' color='secondary'><Term>Ставка</Term></Typography.Text></dt>
          <dd><Typography.Text view='primary-medium' weight='medium'>от {product.base_rate}%</Typography.Text></dd>
        </div>
        <div>
          <dt><Typography.Text view='primary-small' color='secondary'><Term>Срок</Term></Typography.Text></dt>
          <dd><Typography.Text view='primary-medium' weight='medium'>{product.min_term_months}–{product.max_term_months} мес.</Typography.Text></dd>
        </div>
      </dl>
      <div className={styles.needs}>
        <Typography.Text view='primary-small' weight='medium' tag='p' defaultMargins={false}>Вам понадобится</Typography.Text>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>ИНН компании</Typography.Text>
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>Код из СМС для подписи</Typography.Text>
      </div>
      <div className={styles.offerActions}>
        {applyButton}
        <Button view='transparent' size={40} block={true} onClick={() => setPrecheck(true)}>Узнать шансы по ИНН</Button>
      </div>
    </aside>
  );
}
