'use client';

import { useEffect, useState } from 'react';
import {
  fetchTeacherClasses,
  fetchTeacherPlaythroughs,
  type ClassInfo,
  type PlaythroughRecord,
} from '../lib/classroomApi';
import { useRequireAuth } from '../components/auth/AuthProvider';

type Options = {
  classId?: number | '';
  status?: string;
};

export function useTeacherPlaythroughData(options: Options = {}) {
  const { ready, user } = useRequireAuth(['teacher']);
  const [classes, setClasses] = useState<ClassInfo[]>([]);
  const [items, setItems] = useState<PlaythroughRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const classId = options.classId ?? '';
  const status = options.status ?? '';

  useEffect(() => {
    if (!ready) return;
    void (async () => {
      try {
        const cls = await fetchTeacherClasses();
        setClasses(cls);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载班级失败');
      }
    })();
  }, [ready]);

  useEffect(() => {
    if (!ready) return;
    void (async () => {
      setLoading(true);
      setError('');
      try {
        const list = await fetchTeacherPlaythroughs({
          class_id: classId === '' ? undefined : classId,
          status: status || undefined,
        });
        setItems(list);
      } catch (e) {
        setError(e instanceof Error ? e.message : '加载记录失败');
      } finally {
        setLoading(false);
      }
    })();
  }, [ready, classId, status]);

  return { ready, user, classes, items, loading, error };
}
