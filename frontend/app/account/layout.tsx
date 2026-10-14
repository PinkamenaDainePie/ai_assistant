'use client';

import { ConsoleLayout } from '../../components/auth/ConsoleLayout';

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return <ConsoleLayout variant="student">{children}</ConsoleLayout>;
}
