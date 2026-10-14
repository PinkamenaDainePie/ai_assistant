import React from 'react';

type IconProps = {
  className?: string;
};

/** 中西财政对照：天平 + 东西方半球示意 */
export const PortalCompareIcon: React.FC<IconProps> = ({ className }) => (
  <svg className={className} viewBox="0 0 48 48" fill="none" aria-hidden>
    <path
      d="M24 8v28M12 36h24"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <path
      d="M24 8L14 20h20L24 8z"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinejoin="round"
    />
    <path
      d="M10 22h8l-4 10-4-10zM30 22h8l-4 10-4-10z"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinejoin="round"
    />
    <circle cx="14" cy="14" r="3.5" stroke="currentColor" strokeWidth="1.5" />
    <path
      d="M34 11v6M31 14h6"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
  </svg>
);

/** 历代改革时间轴 */
export const PortalTimelineIcon: React.FC<IconProps> = ({ className }) => (
  <svg className={className} viewBox="0 0 48 48" fill="none" aria-hidden>
    <path
      d="M8 24h32"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    />
    <circle cx="10" cy="24" r="3.5" fill="currentColor" />
    <circle cx="22" cy="24" r="3.5" fill="currentColor" opacity="0.75" />
    <circle cx="34" cy="24" r="3.5" fill="currentColor" opacity="0.55" />
    <path
      d="M10 14v6M22 18v4M34 18v4"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      opacity="0.7"
    />
    <rect x="6" y="30" width="10" height="6" rx="2" stroke="currentColor" strokeWidth="1.5" />
    <rect x="18" y="30" width="10" height="6" rx="2" stroke="currentColor" strokeWidth="1.5" opacity="0.8" />
    <rect x="30" y="30" width="10" height="6" rx="2" stroke="currentColor" strokeWidth="1.5" opacity="0.6" />
  </svg>
);

/** 史家对话：卷轴 */
export const PortalScrollIcon: React.FC<IconProps> = ({ className }) => (
  <svg className={className} viewBox="0 0 48 48" fill="none" aria-hidden>
    <path
      d="M12 10c0-2 1.5-3 4-3h16c2.5 0 4 1 4 3v28c0 2-1.5 3-4 3H16c-2.5 0-4-1-4-3V10z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    <path d="M10 12h4M10 36h4M34 12h4M34 36h4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    <path
      d="M18 18h12M18 24h12M18 30h8"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      opacity="0.85"
    />
  </svg>
);

/** AI 助教：典籍 */
export const PortalBookIcon: React.FC<IconProps> = ({ className }) => (
  <svg className={className} viewBox="0 0 48 48" fill="none" aria-hidden>
    <path
      d="M10 12c0-2 2-3 5-3 4 0 7 1 9 3 2-2 5-3 9-3 3 0 5 1 5 3v26c-2-1-5-2-9-2s-7 1-9 2c-2-1-5-2-9-2s-7 1-9 2V12z"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinejoin="round"
    />
    <path d="M24 12v26" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
    <path
      d="M14 20h6M14 26h6M28 20h6M28 26h4"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      opacity="0.75"
    />
  </svg>
);

/** 制度模拟：诏书 / 印 */
export const PortalEdictIcon: React.FC<IconProps> = ({ className }) => (
  <svg className={className} viewBox="0 0 48 48" fill="none" aria-hidden>
    <rect x="12" y="8" width="24" height="32" rx="3" stroke="currentColor" strokeWidth="2" />
    <path
      d="M18 16h12M18 22h12M18 28h8"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
    />
    <rect x="28" y="28" width="10" height="10" rx="1.5" stroke="currentColor" strokeWidth="1.75" />
    <path d="M31 33h4M33 31v4" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
  </svg>
);
