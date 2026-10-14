'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { UserAvatarMenu } from './UserAvatarMenu';
import { useAuth } from './AuthProvider';

export type ConsoleVariant = 'teacher' | 'student';

type NavItem = {
  href: string;
  label: string;
  match: (path: string) => boolean;
};

const TEACHER_NAV: NavItem[] = [
  { href: '/teacher/overview', label: '班级概览', match: (p) => p === '/teacher/overview' },
  {
    href: '/teacher',
    label: '学生记录',
    match: (p) => p === '/teacher' || p.startsWith('/teacher/playthroughs'),
  },
  { href: '/teacher/pending', label: '待评记录', match: (p) => p === '/teacher/pending' },
  { href: '/teacher/grades', label: '成绩汇总', match: (p) => p === '/teacher/grades' },
];

const STUDENT_NAV: NavItem[] = [
  { href: '/account', label: '个人中心', match: (p) => p === '/account' || p.startsWith('/account/') },
  { href: '/', label: '返回课堂', match: () => false },
];

type ConsoleLayoutProps = {
  variant: ConsoleVariant;
  children: React.ReactNode;
};

export const ConsoleLayout: React.FC<ConsoleLayoutProps> = ({ variant, children }) => {
  const pathname = usePathname();
  const { user } = useAuth();
  const nav = variant === 'teacher' ? TEACHER_NAV : STUDENT_NAV;

  useEffect(() => {
    document.documentElement.classList.add('ui-console-root');
    return () => document.documentElement.classList.remove('ui-console-root');
  }, []);

  const pageTitle =
    variant === 'teacher'
      ? pathname.startsWith('/teacher/playthroughs')
        ? '记录详情'
        : pathname === '/teacher/overview'
          ? '班级概览'
          : pathname === '/teacher/pending'
            ? '待评记录'
            : pathname === '/teacher/grades'
              ? '成绩汇总'
              : '学生记录'
      : '个人中心';

  return (
    <div className="ui-console">
      <aside className="ui-console__sidebar">
        <div className="ui-console__brand">
          <span className="ui-console__brand-mark">财</span>
          <div>
            <div className="ui-console__brand-title">中国财税史</div>
            <div className="ui-console__brand-sub">
              {variant === 'teacher' ? '教师工作台' : '学生学习台'}
            </div>
          </div>
        </div>

        <nav className="ui-console__nav" aria-label="控制台导航">
          {nav.map((item) => {
            const active = item.match(pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`ui-console__nav-item${active ? ' ui-console__nav-item--active' : ''}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="ui-console__sidebar-foot">
          <div className="ui-console__user-line">{user?.name}</div>
          <div className="ui-console__user-email">{user?.email}</div>
        </div>
      </aside>

      <div className="ui-console__main">
        <header className="ui-console__topbar">
          <h1 className="ui-console__page-title">{pageTitle}</h1>
          <UserAvatarMenu />
        </header>
        <div className="ui-console__body">{children}</div>
      </div>
    </div>
  );
};
