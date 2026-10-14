'use client';

import React, { useEffect, useState } from 'react';
import { MingFullscreenModal } from './MingFullscreenModal';
import { MingExtractionView } from './MingExtractionView';
import { mingFetchTurnExtraction } from '../../lib/mingApi';
import type { MingExtractionData } from '../../game/ming/mingTurnPhase';

type Props = {
  onClose: () => void;
};

export const MingExtractionModal: React.FC<Props> = ({ onClose }) => {
  const [data, setData] = useState<MingExtractionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    void mingFetchTurnExtraction()
      .then((d) => {
        if (alive) setData(d);
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <MingFullscreenModal title="邸报详明" subtitle="数项加减/账目明细" onClose={onClose}>
      <MingExtractionView data={data} loading={loading} error={error} />
    </MingFullscreenModal>
  );
};
