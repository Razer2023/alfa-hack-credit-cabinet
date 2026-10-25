import { useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Plate } from '@alfalab/core-components/plate';
import { Textarea } from '@alfalab/core-components/textarea';
import { Typography } from '@alfalab/core-components/typography';

import { api, errorMessage } from '../../api/client';
import type { Application, DocumentItem, DocumentRequest, Product } from '../../api/types';
import { CompanyStep } from './CompanyStep';
import { DocumentUpload } from './DocumentUpload';
import { LoanFields } from './LoanFields';
import { type LoanTerms, termsError } from './loanTerms';

type NeedInfoFormProps = {
  application: Application;
  product: Product | undefined;
  onChange: (application: Application) => void;
};

const LOAN_FIELDS = new Set(['amount', 'term_months', 'purpose']);

// Банк просит дополнить заявку (NEED_INFO): что именно — в need_info.items
export function NeedInfoForm({ application, product, onChange }: NeedInfoFormProps) {
  const needInfo = application.need_info;
  const items = needInfo?.items ?? [];
  const asksCompany = items.some((item) => item.field === 'company');
  const asksLoan = items.some((item) => LOAN_FIELDS.has(item.field));
  const documents = items.filter((item) => item.document);
  const questions = items.filter(
    (item) => !item.document && item.field !== 'company' && !LOAN_FIELDS.has(item.field),
  );

  const [terms, setTerms] = useState<LoanTerms>({
    amount: application.amount,
    term: application.term_months ? String(application.term_months) : '',
    purpose: application.purpose ?? '',
  });
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Статус загрузки по каждому запрошенному документу: ключ — «запрос:код»
  const [uploads, setUploads] = useState<Record<string, DocumentItem>>({});

  function rememberUploads(requests: DocumentRequest[]) {
    setUploads((current) => {
      const next = { ...current };
      for (const request of requests) for (const doc of request.items) next[`${request.id}:${doc.code}`] = doc;
      return next;
    });
  }

  const hasDocuments = documents.length > 0;
  useEffect(() => {
    if (!hasDocuments) return;
    api<DocumentRequest[]>(`/applications/${application.id}/documents`).then(rememberUploads).catch(() => undefined);
  }, [application.id, hasDocuments]);

  const errors = termsError(product, terms);
  const missingAnswer = questions.some((item) => !answers[item.field]?.trim());
  const missingCompany = asksCompany && !application.form.company;
  const uploadOf = (item: (typeof documents)[number]) =>
    item.document ? uploads[`${item.document.request_id}:${item.document.code}`] : undefined;
  const missingDocument = documents.some((item) => uploadOf(item)?.status !== 'RECEIVED');
  const disabled = missingAnswer || missingCompany || missingDocument || Boolean(errors.amount || errors.term);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      const body = {
        amount: terms.amount ?? undefined,
        term_months: Number(terms.term) || undefined,
        purpose: terms.purpose.trim() || undefined,
        extra: answers,
        comment: comment.trim() || undefined,
      };
      onChange(await api<Application>(`/applications/${application.id}/info`, { method: 'POST', body }));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Plate view='attention' rounded={true} border={true} title='Банку нужны дополнительные данные'>
      <ul>
        {items.filter((item) => !item.document).map((item) => (
          <li key={item.field}>
            <Typography.Text view='primary-medium'>{item.message}</Typography.Text>
          </li>
        ))}
      </ul>
      {needInfo?.comment && (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Комментарий банка: {needInfo.comment}
        </Typography.Text>
      )}

      {hasDocuments && (
        <>
          <Gap size={8} />
          <Typography.Text view='primary-medium' weight='bold' tag='p' defaultMargins={false}>
            Загрузите документы
          </Typography.Text>
          {documents.map((item) => (
            <div key={item.field}>
              <Gap size={12} />
              <DocumentUpload
                applicationId={application.id}
                item={item}
                uploaded={uploadOf(item)}
                onUploaded={(request) => rememberUploads([request])}
              />
            </div>
          ))}
        </>
      )}
      {asksCompany && (
        <>
          <Gap size={16} />
          <CompanyStep application={application} onChange={onChange} />
        </>
      )}
      {asksLoan && (
        <>
          <Gap size={16} />
          <LoanFields product={product} terms={terms} onChange={setTerms} />
        </>
      )}
      {questions.map((item) => (
        <div key={item.field}>
          <Gap size={16} />
          <Textarea
            label={item.message}
            block={true}
            minRows={2}
            maxLength={1000}
            value={answers[item.field] ?? ''}
            onChange={(_, { value }) => setAnswers({ ...answers, [item.field]: value })}
          />
        </div>
      ))}
      <Gap size={16} />
      <Textarea
        label='Комментарий для банка (необязательно)'
        block={true}
        minRows={2}
        maxLength={1000}
        value={comment}
        onChange={(_, { value }) => setComment(value)}
      />
      <Gap size={16} />
      <Button view='accent' size={48} loading={busy} disabled={disabled} onClick={submit}>
        Отправить данные
      </Button>
      {error && (
        <>
          <Gap size={8} />
          <Typography.Text view='primary-small' color='negative'>
            {error}
          </Typography.Text>
        </>
      )}
    </Plate>
  );
}
