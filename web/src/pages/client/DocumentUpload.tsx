import { useState } from 'react';
import { Attach } from '@alfalab/core-components/attach';
import { Gap } from '@alfalab/core-components/gap';
import { Status } from '@alfalab/core-components/status';
import { Typography } from '@alfalab/core-components/typography';

import { apiUpload, errorMessage } from '../../api/client';
import type { DocumentItem, DocumentRequest, InfoItem } from '../../api/types';
import styles from './Forms.module.css';

type DocumentUploadProps = {
  applicationId: string;
  item: InfoItem;
  uploaded: DocumentItem | undefined;
  onUploaded: (request: DocumentRequest) => void;
};

// Один запрошенный документ: что нужно, зачем (J9) и загрузка файла (S4.7)
export function DocumentUpload({ applicationId, item, uploaded, onUploaded }: DocumentUploadProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const document = item.document;
  if (!document) return null;
  const received = uploaded?.status === 'RECEIVED';

  async function upload(files: File[]) {
    const [file] = files;
    if (!file || !document) return;
    setBusy(true);
    setError(null);
    try {
      const path = `/applications/${applicationId}/documents/${document.request_id}/${document.code}`;
      onUploaded(await apiUpload<DocumentRequest>(path, file));
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className={styles.document}>
      <div className={styles.documentHeader}>
        <Typography.Text view='primary-medium' weight='bold'>
          {item.message}
        </Typography.Text>
        <Status view='soft' color={received ? 'green' : 'orange'} size={20}>
          {received ? 'Загружен' : 'Нужен файл'}
        </Status>
      </div>
      {item.reason && (
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Зачем: {item.reason}
        </Typography.Text>
      )}
      <Gap size={8} />
      <Attach
        size={40}
        accept='.pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png'
        buttonContent={received ? 'Заменить файл' : 'Выбрать файл'}
        noFileText={received && uploaded?.filename ? uploaded.filename : 'PDF, JPEG или PNG до 5 МБ'}
        disabled={busy}
        onChange={(_, { files }) => upload(files)}
      />
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
    </div>
  );
}
