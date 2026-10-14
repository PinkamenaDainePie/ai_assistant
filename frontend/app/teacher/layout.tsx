'use client';

import { ConsoleLayout } from '../../components/auth/ConsoleLayout';

export default function TeacherLayout({ children }: { children: React.ReactNode }) {
  return <ConsoleLayout variant="teacher">{children}</ConsoleLayout>;
}
