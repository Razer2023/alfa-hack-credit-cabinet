import { useEffect, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Plate } from '@alfalab/core-components/plate';
import { Status } from '@alfalab/core-components/status';
import { Typography } from '@alfalab/core-components/typography';

import { api, apiDownload, errorMessage } from '../../api/client';
import type { DocumentRequest } from '../../api/types';
import styles from './Bank.module.css';

type DocumentsPanelProps = {
  applicationId: string;
  // Меняется при каждом событии по заявке — панель перечитывает документы
  version: number;
};

// Запрошенные документы и файлы клиента (S4.4, S4.7)
export function DocumentsPanel({ applicationId, version }: DocumentsPanelProps) {
  const [requests, setRequests] = useState<DocumentRequest[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<DocumentRequest[]>(`/bank/applications/${applicationId}/documents`)
      .then(setRequests)
      .catch((e) => setError(errorMessage(e)));
  }, [applicationId, version]);

  if (requests.length === 0 && !error) return null;

  async function download(requestId: string, code: string, filename: string) {
    try {
      await apiDownload(`/bank/applications/${applicationId}/documents/${requestId}/${code}`, filename);
    } catch (e) {
      setError(errorMessage(e));
    }
  }

  return (
    <Plate view='common' rounded={true} border={true} title='Документы клиента'>
      {error && (
        <Typography.Text view='primary-small' color='negative' tag='p' defaultMargins={false}>
          {error}
        </Typography.Text>
      )}
      {requests.map((request) =>
        request.items.map((item) => (
          <div key={`${request.id}:${item.code}`} className={styles.documentRow}>
            <div>
              <Typography.Text view='primary-small' weight='bold' tag='p' defaultMargins={false}>
                {item.title}
              </Typography.Text>
              {item.reason && (
                <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
                  Зачем: {item.reason}
                </Typography.Text>
              )}
            </div>
            {item.status === 'RECEIVED' ? (
              <Button
                view='secondary'
                size={32}
                onClick={() => download(request.id, item.code, item.filename ?? item.code)}
              >
                Скачать
              </Button>
            ) : (
              <Status view='soft' color='orange' size={20}>
                Ждём от клиента
              </Status>
            )}
          </div>
        )),
      )}
    </Plate>
  );
}
