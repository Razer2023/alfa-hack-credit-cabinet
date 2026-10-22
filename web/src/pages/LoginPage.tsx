import { type FormEvent, useState } from 'react';
import { Button } from '@alfalab/core-components/button';
import { Gap } from '@alfalab/core-components/gap';
import { Input } from '@alfalab/core-components/input';
import { Plate } from '@alfalab/core-components/plate';
import { Typography } from '@alfalab/core-components/typography';

import { errorMessage } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import styles from './LoginPage.module.css';

const DEMO_USERS = [
  { login: 'coffee', who: 'Кофейня — одобрение' },
  { login: 'stroy', who: 'Стройка — контрпредложение' },
  { login: 'vector', who: 'Вектор — ручное рассмотрение' },
  { login: 'manager', who: 'менеджер банка' },
  { login: 'underwriter', who: 'андеррайтер' },
];

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
      <Plate view='common' rounded={true} border={true} title='Вход в кредитный кабинет'>
        <form onSubmit={submit}>
          <Input
            label='Логин'
            block={true}
            autoComplete='username'
            value={loginName}
            onChange={(_, { value }) => setLoginName(value)}
          />
          <Gap size={12} />
          <Input
            label='Пароль'
            type='password'
            block={true}
            autoComplete='current-password'
            value={password}
            error={error ?? undefined}
            onChange={(_, { value }) => setPassword(value)}
          />
          <Gap size={16} />
          <Button type='submit' view='accent' size={48} block={true} loading={busy} disabled={!loginName || !password}>
            Войти
          </Button>
        </form>
        <Gap size={16} />
        <Typography.Text view='primary-small' color='secondary' tag='p' defaultMargins={false}>
          Демо-пользователи (пароль — CORE_DEMO_PASSWORD из .env):
        </Typography.Text>
        <ul className={styles.demo}>
          {DEMO_USERS.map((user) => (
            <li key={user.login}>
              <Typography.Text view='primary-small'>
                <b>{user.login}</b> — {user.who}
              </Typography.Text>
            </li>
          ))}
        </ul>
      </Plate>
    </div>
  );
}
