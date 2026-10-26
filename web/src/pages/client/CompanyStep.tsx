import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Input } from '@alfalab/core-components/input';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application } from '../../api/types';
import { useUser } from '../../auth/AuthContext';
import { Term } from '../../components/Term';
import { COMPANY_FIELDS, SOURCE_LABEL, formatCompanyValue } from '../../format';
import styles from './Forms.module.css';

type CompanyStepProps = {
  application: Application;
  onChange: (application: Application) => void;
};

// Заполнение анкеты по ИНН из ЕГРЮЛ, ФНС и выписки (S3.1)
export function CompanyStep({ application, onChange }: CompanyStepProps) {
  const user = useUser();
  const [inn, setInn] = useState(user.company?.inn ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const company = application.form.company;

  async function prefill() {
    setBusy(true);
    setError(null);
    try {
      onChange(await api<Application>(`/applications/${application.id}/prefill`, { method: 'POST', body: { inn } }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className={styles.row}>
        <Input
          label='ИНН компании'
          block={true}
          value={inn}
          inputMode='numeric'
          maxLength={12}
          error={error ?? undefined}
          hint='Данные подтянем из ЕГРЮЛ, ФНС и выписки — вводить вручную не нужно'
          onChange={(_, { value }) => setInn(value.replace(/\D/g, ''))}
        />
        <Button view={company ? 'secondary' : 'accent'} size={56} loading={busy} onClick={prefill}>
          {company ? 'Обновить данные' : 'Заполнить по ИНН'}
        </Button>
      </div>
      {company && (
        <dl className={styles.company} aria-label='Данные компании'>
          {Object.entries(company).map(([field, { value, source }]) => (
            <div key={field} className={styles.companyRow}>
              <dt>
                <Typography.Text view='primary-small' color='secondary'>
                  <Term>{COMPANY_FIELDS[field] ?? field}</Term>
                </Typography.Text>
              </dt>
              <dd>
                <Typography.Text view='primary-medium' weight='medium'>{formatCompanyValue(field, value)}</Typography.Text>
              </dd>
              <dd className={styles.source}>
                <Typography.Text view='primary-small' color='secondary'>
                  <Term name={SOURCE_LABEL[source]}>{SOURCE_LABEL[source]}</Term>
                </Typography.Text>
              </dd>
            </div>
          ))}
        </dl>
      )}
    </>
  );
}
