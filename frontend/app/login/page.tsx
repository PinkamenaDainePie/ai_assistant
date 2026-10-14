'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../components/auth/AuthProvider';
import { AuthVideoBackground } from '../../components/auth/AuthVideoBackground';
import { getSwufeSsoStartUrl } from '../../lib/classroomApi';

type AuthMode = 'login' | 'register';

export default function LoginPage() {
  const router = useRouter();
  const { config, user, loading, login, register } = useAuth();
  const [mode, setMode] = useState<AuthMode>('login');
  const [name, setName] = useState('');
  const [studentId, setStudentId] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (loading) return;
    if (!config.enabled) {
      router.replace('/');
      return;
    }
    if (user) {
      router.replace(user.role === 'teacher' ? '/teacher' : '/');
    }
  }, [loading, config.enabled, user, router]);

  const redirectAfterAuth = (role: string) => {
    router.replace(role === 'teacher' ? '/teacher' : '/');
  };

  const onLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const u = await login(email.trim(), password);
      redirectAfterAuth(u.role);
    } catch (err) {
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setSubmitting(false);
    }
  };

  const onRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }
    if (password.length < 4) {
      setError('密码至少 4 位');
      return;
    }
    if (!registerOpen) {
      setError('注册暂未开放，请联系任课教师');
      return;
    }
    setSubmitting(true);
    try {
      const u = await register({
        email: email.trim(),
        password,
        name: name.trim(),
        student_id: studentId.trim() || undefined,
      });
      redirectAfterAuth(u.role);
    } catch (err) {
      setError(err instanceof Error ? err.message : '注册失败');
    } finally {
      setSubmitting(false);
    }
  };

  const onCampusLogin = () => {
    window.location.href = getSwufeSsoStartUrl();
  };

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setError('');
    setConfirmPassword('');
  };

  const showLocalLogin = config.allow_local_login;
  const showCampusLogin = config.swufe_sso_enabled;
  const showRegisterUi = showLocalLogin;
  const registerOpen = config.allow_register;

  if (loading || !config.enabled) {
    return (
      <main className="ui-auth-page">
        <AuthVideoBackground />
        <p className="ui-muted ui-auth-page__status ui-auth-page__status--pulse">加载中…</p>
      </main>
    );
  }

  return (
    <main className="ui-auth-page">
      <AuthVideoBackground />

      <div className="ui-auth-modal ui-auth-modal--enter">
        <aside className="ui-auth-brand">
          <div className="ui-auth-brand__seal" aria-hidden>
            财
          </div>
          <h2 className="ui-auth-brand__title ui-auth-brand__title--enter">中国财税史</h2>
          <p className="ui-auth-brand__tagline ui-auth-brand__tagline--enter">智慧课堂</p>
        </aside>

        <section className="ui-auth-panel">
          {showRegisterUi ? (
            <div
              className="ui-auth-mode-switch"
              role="tablist"
              aria-label="登录或注册"
              data-active={mode}
            >
              <span className="ui-auth-mode-switch__indicator" aria-hidden />
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'login'}
                className={`ui-auth-mode-switch__btn${mode === 'login' ? ' ui-auth-mode-switch__btn--active' : ''}`}
                onClick={() => switchMode('login')}
              >
                登录
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'register'}
                className={`ui-auth-mode-switch__btn${mode === 'register' ? ' ui-auth-mode-switch__btn--active' : ''}`}
                onClick={() => switchMode('register')}
              >
                注册
              </button>
            </div>
          ) : (
            <h1 className="ui-auth-panel__title ui-auth-panel__title--enter">登录</h1>
          )}

          <div key={mode} className="ui-auth-form-stage ui-auth-form-stage--enter">
          {showCampusLogin && mode === 'login' ? (
            <>
              <button type="button" className="ui-btn ui-btn--primary" onClick={onCampusLogin}>
                使用校园账号登录
              </button>
              {showLocalLogin ? (
                <p className="ui-auth-panel__lead ui-auth-panel__lead--divider">或使用邮箱账号</p>
              ) : null}
            </>
          ) : null}

          {showLocalLogin && mode === 'login' ? (
            <form onSubmit={onLogin} className="ui-form">
              <div className="ui-field">
                <label className="ui-label" htmlFor="login-email">
                  邮箱
                </label>
                <input
                  id="login-email"
                  className="ui-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.edu"
                  autoComplete="username"
                  required
                />
              </div>

              <div className="ui-field">
                <label className="ui-label" htmlFor="login-password">
                  密码
                </label>
                <input
                  id="login-password"
                  className="ui-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  required
                />
              </div>

              {error ? (
                <p className="ui-error ui-error--enter" role="alert">
                  {error}
                </p>
              ) : null}

              <button type="submit" className="ui-btn ui-btn--primary" disabled={submitting}>
                {submitting ? '登录中…' : '进入课堂'}
              </button>
            </form>
          ) : null}

          {showRegisterUi && mode === 'register' ? (
            <form onSubmit={onRegister} className="ui-form">
              {!registerOpen ? (
                <p className="ui-muted">注册暂未开放，请使用演示账号或联系任课教师。</p>
              ) : null}
              <div className="ui-field">
                <label className="ui-label" htmlFor="register-name">
                  姓名
                </label>
                <input
                  id="register-name"
                  className="ui-input"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="张三"
                  autoComplete="name"
                  required
                />
              </div>

              <div className="ui-field">
                <label className="ui-label" htmlFor="register-student-id">
                  学号
                </label>
                <input
                  id="register-student-id"
                  className="ui-input"
                  type="text"
                  value={studentId}
                  onChange={(e) => setStudentId(e.target.value)}
                  placeholder="20250001（可选）"
                  autoComplete="off"
                />
              </div>

              <div className="ui-field">
                <label className="ui-label" htmlFor="register-email">
                  邮箱
                </label>
                <input
                  id="register-email"
                  className="ui-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@example.edu"
                  autoComplete="email"
                  required
                />
              </div>

              <div className="ui-field">
                <label className="ui-label" htmlFor="register-password">
                  密码
                </label>
                <input
                  id="register-password"
                  className="ui-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="至少 4 位"
                  autoComplete="new-password"
                  minLength={4}
                  required
                />
              </div>

              <div className="ui-field">
                <label className="ui-label" htmlFor="register-confirm-password">
                  确认密码
                </label>
                <input
                  id="register-confirm-password"
                  className="ui-input"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="再次输入密码"
                  autoComplete="new-password"
                  minLength={4}
                  required
                />
              </div>

              {error ? (
                <p className="ui-error ui-error--enter" role="alert">
                  {error}
                </p>
              ) : null}

              <button
                type="submit"
                className="ui-btn ui-btn--primary"
                disabled={submitting || !registerOpen}
              >
                {submitting ? '注册中…' : '注册并进入课堂'}
              </button>
            </form>
          ) : null}

          {showLocalLogin && mode === 'login' ? (
            <p className="ui-legal ui-legal--compact">
              演示：<strong>student1@demo.edu</strong> / <strong>demo1234</strong>
            </p>
          ) : null}

          {showRegisterUi && mode === 'register' ? (
            <p className="ui-legal ui-legal--compact">
              已有账号？{' '}
              <button type="button" className="ui-link ui-link--inline" onClick={() => switchMode('login')}>
                去登录
              </button>
            </p>
          ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}
