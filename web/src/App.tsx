import { useEffect } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Typography } from '@alfalab/core-components/typography';

import { getToken } from './api/client';
import { useAuth, useUser } from './auth/AuthContext';
import { AuthProvider } from './auth/AuthProvider';
import { EventToast } from './components/EventToast';
import { openEventStream } from './events';
import { Layout, NavLink } from './layout/Layout';
import { BankCard } from './pages/bank/BankCard';
import { BankHome } from './pages/bank/BankHome';
import { Dashboard } from './pages/bank/Dashboard';
import { ApplicationPage } from './pages/client/ApplicationPage';
import { ClientHome } from './pages/client/ClientHome';
import { LoginPage } from './pages/LoginPage';
import { matchRoute, navigate, useRoute } from './router';
import { useInvertedOnDark } from './theme/ThemeContext';
import { ThemeProvider } from './theme/ThemeProvider';

export function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </ThemeProvider>
  );
}

// Интерфейс выбирает роль: CLIENT — кабинет клиента, MANAGER / UNDERWRITER — рабочее место банка
function Shell() {
  const { user, logout } = useAuth();
  const path = useRoute();
  const inverted = useInvertedOnDark();

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

  // Тёмные только обзор и кредиты клиента: у них тёмный первый экран и белый лист поверх.
  // Аналитика банка — в общей теме кабинета, но со своей раскладкой на всю ширину.
  const client = user.role === 'CLIENT';
  const analytics = !client && path === '/dashboard';
  const tone = client && (path === '/' || path === '/products') ? 'dark' : 'light';

  return (
    <Layout
      tone={tone}
      bleed={tone === 'dark' || analytics}
      navigation={client ? <>
        <NavLink tone={tone} href='#/' current={path !== '/products'}>Обзор</NavLink>
        <NavLink tone={tone} href='#/products' current={path === '/products'}>Кредитные продукты</NavLink>
      </> : <>
        <NavLink tone={tone} href='#/' current={path !== '/dashboard'}>Заявки</NavLink>
        <NavLink tone={tone} href='#/dashboard' current={path === '/dashboard'}>Аналитика</NavLink>
      </>}
      actions={
        <>
          <Typography.Text view='primary-small' color={tone === 'dark' ? 'secondary-inverted' : 'secondary'}>
            {user.company?.name ?? user.full_name}
          </Typography.Text>
          <Button
            view='secondary'
            colors={tone === 'dark' && inverted ? 'inverted' : 'default'}
            size={40}
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
