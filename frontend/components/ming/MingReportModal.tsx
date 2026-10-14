'use client';

import React from 'react';
import { MingFullscreenModal } from './MingFullscreenModal';
import { formatMingReportText } from '../../game/ming/mingReportFormat';

type Props = {
  report: string;
  onClose: () => void;
  title?: string;
  subtitle?: string;
};

export const MingReportModal: React.FC<Props> = ({
  report,
  onClose,
  title = '月末奏疏',
  subtitle = '推演结果',
}) => (
  <MingFullscreenModal wide title={title} subtitle={subtitle} onClose={onClose}>
    <pre
      style={{
        whiteSpace: 'pre-wrap',
        fontSize: 13,
        lineHeight: 1.7,
        color: '#ddd',
        fontFamily: 'inherit',
        margin: 0,
      }}
    >
      {formatMingReportText(report)}
    </pre>
  </MingFullscreenModal>
);
