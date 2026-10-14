'use client';

import React from 'react';

type PortalModuleOverlayProps = {
  open: boolean;
  title: string;
  subtitle?: string;
  tone?: 'purple' | 'blue' | 'pink' | 'gold' | 'green';
  onClose: () => void;
  children: React.ReactNode;
};

export const PortalModuleOverlay: React.FC<PortalModuleOverlayProps> = ({
  open,
  title,
  subtitle,
  tone = 'purple',
  onClose,
  children,
}) => {
  if (!open) return null;

  return (
    <div className="portal-overlay" role="dialog" aria-modal="true" aria-labelledby="portal-overlay-title">
      <div className="portal-overlay__backdrop" onClick={onClose} aria-hidden />
      <div className={`portal-overlay__panel portal-overlay__panel--${tone}`}>
        <div className="portal-overlay__header">
          <div>
            <h2 id="portal-overlay-title" className="portal-overlay__title">
              {title}
            </h2>
            {subtitle ? <p className="portal-overlay__subtitle">{subtitle}</p> : null}
          </div>
          <button type="button" className="portal-overlay__close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>
        <div className="portal-overlay__body">{children}</div>
      </div>
    </div>
  );
};
