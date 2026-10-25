import { Gap } from '@alfalab/core-components/gap';
import { Status } from '@alfalab/core-components/status';

import type { CompanyField } from '../api/types';
import { COMPANY_FIELDS, SOURCE_LABEL, formatCompanyValue } from '../format';
import { FactList } from './FactList';
import { Term } from './Term';

type CompanyFactsProps = {
  company: Record<string, CompanyField>;
};

// Данные компании по ИНН с бейджем источника (S3.1)
export function CompanyFacts({ company }: CompanyFactsProps) {
  const facts = Object.entries(company).map(([field, { value, source }]) => ({
    label: COMPANY_FIELDS[field] ?? field,
    value: (
      <>
        {formatCompanyValue(field, value)}
        <Gap size={4} />
        <Term name={SOURCE_LABEL[source]}>
          <Status view='muted-alt' color='blue' size={20}>
            {SOURCE_LABEL[source]}
          </Status>
        </Term>
      </>
    ),
  }));
  return <FactList facts={facts} />;
}
