import { useEffect } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import { getToken } from './api/client';
import { useAuth, useUser } from './auth/AuthContext';
import { AuthProvider } from './auth/AuthProvider';
import { EventToast } from './components/EventToast';
import { openEventStream } from './events';
import { Layout } from './layout/Layout';
import { BankCard } from './pages/bank/BankCard';
import { BankHome } from './pages/bank/BankHome';
import { Dashboard } from './pages/bank/Dashboard';
import { ApplicationPage } from './pages/client/ApplicationPage';
import { ClientHome } from './pages/client/ClientHome';
import { LoginPage } from './pages/LoginPage';
import { matchRoute, navigate, useRoute } from './router';

export function App() {
  return (
    <AuthProvider>
      <Shell />
    </AuthProvider>
  );
}

// Интерфейс выбирает роль: CLIENT — кабинет клиента, MANAGER / UNDERWRITER — рабочее место банка
function Shell() {
  const { user, logout } = useAuth();
  const path = useRoute();

  // Одно соединение SSE на всё время входа: статусы обновляются без перезагрузки (S4.5)
  useEffect(() => {
    const token = getToken();
    if (!user || !token) return;
    return openEventStream(token);
  }, [user]);

  if (!user) {
    return (
      <Layout>
        <LoginPage />
      </Layout>
    );
  }

  return (
    <Layout
      navigation={user.role === 'CLIENT' ? <>
        <Button view={path === '/products' ? 'transparent' : 'secondary'} size={40} href='#/' aria-current={path === '/' ? 'page' : undefined}>Обзор</Button>
        <Button view={path === '/products' ? 'secondary' : 'transparent'} size={40} href='#/products' aria-current={path === '/products' ? 'page' : undefined}>Кредитные продукты</Button>
      </> : <>
        <Button view={path === '/dashboard' ? 'transparent' : 'secondary'} size={40} href='#/' aria-current={path === '/dashboard' ? undefined : 'page'}>Заявки</Button>
        <Button view={path === '/dashboard' ? 'secondary' : 'transparent'} size={40} href='#/dashboard' aria-current={path === '/dashboard' ? 'page' : undefined}>Узкие места</Button>
      </>}
      actions={
        <>
          <Typography.Text view='primary-small' color='secondary'>
            {user.company?.name ?? user.full_name}
          </Typography.Text>
          <Button
            view='secondary'
            size={32}
            onClick={() => {
              logout();
              navigate('/');
            }}
          >
            Выйти
          </Button>
        </>
      }
    >
      <EventToast />
      <Routes />
    </Layout>
  );
}

function Routes() {
  const user = useUser();
  const path = useRoute();

  if (user.role === 'CLIENT') {
    const application = matchRoute('/applications/:id', path);
    return application ? <ApplicationPage key={application.id} id={application.id} /> : <ClientHome />;
  }
  if (path === '/dashboard') return <Dashboard />;
  const card = matchRoute('/bank/:id', path);
  return card ? <BankCard key={card.id} id={card.id} /> : <BankHome />;
}
