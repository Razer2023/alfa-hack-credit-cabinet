import { useState } from 'react';
import { Tab, Tabs, type TabsProps } from '@alfalab/core-components/tabs';

import { Layout } from './layout/Layout';
import { BankHome } from './pages/BankHome';
import { ClientHome } from './pages/ClientHome';

// Пока нет входа, интерфейс переключается вручную. После подключения API
// его будет выбирать роль пользователя: CLIENT — кабинет клиента, MANAGER / UNDERWRITER — банк.
export function App() {
  const [area, setArea] = useState<TabsProps['selectedId']>('client');

  return (
    <Layout>
      <Tabs view='primary' size='s' selectedId={area} onChange={(_, { selectedId }) => setArea(selectedId)}>
        <Tab id='client' title='Клиент'>
          <ClientHome />
        </Tab>
        <Tab id='bank' title='Банк'>
          <BankHome />
        </Tab>
      </Tabs>
    </Layout>
  );
}
