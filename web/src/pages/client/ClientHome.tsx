import { useCallback, useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Spinner } from '@alfalab/core-components/spinner';
import { TBody, TCell, THead, THeadCell, TRow, Table } from '@alfalab/core-components/table';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, Product } from '../../api/types';
import { Money } from '../../components/Money';
import { StatusLabel } from '../../components/StatusLabel';
import { useApplicationEvents } from '../../events';
import { formatDateTime, formatRub } from '../../format';
import { navigate } from '../../router';
import styles from './ClientHome.module.css';

// Кабинет клиента: каталог продуктов (S1.1) и заявки компании
export function ClientHome() {
  const [products, setProducts] = useState<Product[]>([]);
  const [applications, setApplications] = useState<Application[] | null>(null);
  const [creating, setCreating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadApplications = useCallback(() => {
    api<Application[]>('/applications').then(setApplications).catch((e) => setError(errorMessage(e)));
  }, []);

  useEffect(() => {
    api<Product[]>('/products').then(setProducts).catch((e) => setError(errorMessage(e)));
    loadApplications();
  }, [loadApplications]);

  useApplicationEvents(loadApplications);

  async function apply(product: Product) {
    setCreating(product.code);
    setError(null);
    try {
      const created = await api<Application>('/applications', { method: 'POST', body: { product_code: product.code } });
      navigate(`/applications/${created.id}`);
    } catch (e) {
      setError(errorMessage(e));
      setCreating(null);
    }
  }

  const productName = (code: string) => products.find((product) => product.code === code)?.name ?? code;

  return (
    <>
      <Typography.Title tag='h1' view='medium' font='system'>
        Кредиты для бизнеса
      </Typography.Title>
      <Gap size={8} />
      <Typography.Text view='primary-medium' color='secondary' tag='p' defaultMargins={false}>
        Выберите кредит, заполните заявку по ИНН и следите за решением онлайн.
      </Typography.Text>
      {error && (
        <>
          <Gap size={12} />
          <Typography.Text view='primary-small' color='negative'>
            {error}
          </Typography.Text>
        </>
      )}
      <Gap size={24} />

      {products.length === 0 && !error && <Spinner preset={24} visible={true} />}
      <div className={styles.catalog}>
        {products.map((product) => (
          <Plate
            key={product.code}
            view='common'
            rounded={true}
            border={true}
            title={product.name}
            buttons={[
              <Button
                key='apply'
                view='accent'
                size={40}
                loading={creating === product.code}
                disabled={creating !== null}
                onClick={() => apply(product)}
              >
                Оформить
              </Button>,
            ]}
          >
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              {product.description}
            </Typography.Text>
            <Gap size={12} />
            <Typography.Text view='primary-medium' tag='p' defaultMargins={false}>
              {formatRub(product.min_amount)} – {formatRub(product.max_amount)}
            </Typography.Text>
            <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
              {product.min_term_months}–{product.max_term_months} мес. · от {product.base_rate}% годовых
            </Typography.Text>
          </Plate>
        ))}
      </div>

      {applications && applications.length > 0 && (
        <>
          <Gap size={40} />
          <Typography.Title tag='h2' view='small' font='system'>
            Мои заявки
          </Typography.Title>
          <Gap size={16} />
          <Table>
            <THead>
              <THeadCell>Номер</THeadCell>
              <THeadCell>Кредит</THeadCell>
              <THeadCell textAlign='right'>Сумма</THeadCell>
              <THeadCell>Статус</THeadCell>
              <THeadCell>Изменена</THeadCell>
            </THead>
            <TBody>
              {applications.map((application) => (
                <TRow
                  key={application.id}
                  className={styles.row}
                  onClick={() => navigate(`/applications/${application.id}`)}
                >
                  <TCell>{application.number}</TCell>
                  <TCell>{productName(application.product_code)}</TCell>
                  <TCell className={styles.amount}>
                    {application.amount ? <Money value={application.amount} /> : '—'}
                  </TCell>
                  <TCell>
                    <StatusLabel status={application.status} />
                  </TCell>
                  <TCell>{formatDateTime(application.status_changed_at)}</TCell>
                </TRow>
              ))}
            </TBody>
          </Table>
        </>
      )}
    </>
  );
}
