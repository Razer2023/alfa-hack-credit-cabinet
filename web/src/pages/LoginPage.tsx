import { type FormEvent, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Input } from '@alfalab/core-components/input';
import { Typography } from '@alfalab/core-components/typography';

import { errorMessage } from '../api/client';
import alfaMark from '../assets/alfa-mark.svg';
import { useAuth } from '../auth/AuthContext';
import styles from './LoginPage.module.css';

const DEMO_USERS = [
  { login: 'coffee', who: 'Кофейня — одобрение' },
  { login: 'stroy', who: 'Стройка — контрпредложение' },
  { login: 'vector', who: 'Вектор — ручное рассмотрение' },
  { login: 'manager', who: 'Менеджер: подтверждает одобрения' },
  { login: 'underwriter', who: 'Андеррайтер: рисковые заявки и отказы' },
];

// Вход по макету «Кабинет — клиент v2» (8e): светлый фон, белая карточка, демо-доступ под формой
export function LoginPage() {
  const { login } = useAuth();
  const [loginName, setLoginName] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(loginName.trim(), password);
    } catch (e) {
      setError(errorMessage(e));
      setBusy(false);
    }
  }

  return (
    <div className={styles.wrapper}>
      <section className={styles.card} aria-labelledby='login-title'>
        <span className={styles.symbol} aria-hidden='true'><img src={alfaMark} alt='' /></span>
        <Typography.TitleResponsive id='login-title' tag='h1' view='medium' font='system'>
          Вход в кредитный кабинет
        </Typography.TitleResponsive>
        <form className={styles.form} onSubmit={submit}>
          <Input
            label='Логин'
            block={true}
            autoComplete='username'
            value={loginName}
            onChange={(_, { value }) => setLoginName(value)}
          />
          <Input
            label='Пароль'
            type='password'
            block={true}
            autoComplete='current-password'
            value={password}
            error={error ?? undefined}
            onChange={(_, { value }) => setPassword(value)}
          />
          <Button type='submit' view='accent' size={56} block={true} loading={busy} disabled={!loginName || !password}>
            Войти
          </Button>
        </form>
        <div className={styles.demo}>
          <Typography.Text view='primary-small' weight='medium' tag='p' defaultMargins={false}>Демо-доступ</Typography.Text>
          <Typography.Text view='secondary-large' color='secondary' tag='p' defaultMargins={false}>
            Пароль — CORE_DEMO_PASSWORD из .env. Нажмите на логин, чтобы подставить.
          </Typography.Text>
          <ul className={styles.users}>
            {DEMO_USERS.map((user) => (
              <li key={user.login}>
                <button type='button' className={styles.user} onClick={() => setLoginName(user.login)}
                  aria-label={`Подставить логин ${user.login}`}>
                  <Typography.Text className={styles.login} view='primary-small' weight='medium'>{user.login}</Typography.Text>
                  <Typography.Text view='primary-small' color='secondary'>{user.who}</Typography.Text>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </div>
  );
}
