'use client';

import React, { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { AuthVideoBackground } from '../../../components/auth/AuthVideoBackground';
import { completeSsoCallback } from '../../../lib/classroomApi';
import { useAuth } from '../../../components/auth/AuthProvider';

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useAuth();
  const [error, setError] = useState('');

  useEffect(() => {
    const token = searchParams.get('access_token');
    if (!token) {
      setError('登录回调缺少凭证');
      return;
    }
    void (async () => {
      try {
        const user = await completeSsoCallback(token);
        await refresh();
        router.replace(user.role === 'teacher' ? '/teacher' : '/');
      } catch (err) {
        setError(err instanceof Error ? err.message : '校园账号登录失败');
      }
    })();
  }, [searchParams, router, refresh]);

  return (
    <main className="ui-auth-page">
      <AuthVideoBackground />
      <p className={`ui-muted ui-auth-page__status${error ? '' : ' ui-auth-page__status--pulse'}`}>
        {error || '正在完成校园账号登录…'}
      </p>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <main className="ui-auth-page">
          <AuthVideoBackground />
          <p className="ui-muted ui-auth-page__status ui-auth-page__status--pulse">正在完成校园账号登录…</p>
        </main>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}
