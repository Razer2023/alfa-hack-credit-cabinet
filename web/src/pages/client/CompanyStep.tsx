import { useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application } from '../../api/types';
import { useUser } from '../../auth/AuthContext';
import { CompanyFacts } from '../../components/CompanyFacts';
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
          value={inn}
          inputMode='numeric'
          maxLength={12}
          error={error ?? undefined}
          onChange={(_, { value }) => setInn(value.replace(/\D/g, ''))}
          className={styles.inn}
        />
        <Button view={company ? 'secondary' : 'accent'} size={56} loading={busy} onClick={prefill}>
          {company ? 'Обновить данные' : 'Заполнить по ИНН'}
        </Button>
      </div>
      {company ? (
        <>
          <Gap size={16} />
          <CompanyFacts company={company} />
        </>
      ) : (
        <>
          <Gap size={8} />
          <Typography.Text view='primary-small' color='secondary'>
            Подтянем название, руководителя, ОКВЭД и обороты из ЕГРЮЛ, ФНС и выписки по счёту — вводить вручную не нужно.
          </Typography.Text>
        </>
      )}
    </>
  );
}
