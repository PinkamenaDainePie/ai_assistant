'use client';

import React, { useEffect, useState } from 'react';
import { MingFullscreenModal } from './MingFullscreenModal';
import { MingExtractionView } from './MingExtractionView';
import { mingFetchHistoryTurn, mingFetchHistoryTurns } from '../../lib/mingApi';
import { formatMingDetailNarrative } from '../../game/ming/mingReportFormat';
import type { MingHistoryDetail, MingHistoryTurnItem } from '../../game/ming/mingTurnPhase';
type Props = {
  onClose: () => void;
};

export const MingHistoryModal: React.FC<Props> = ({ onClose }) => {
  const [turns, setTurns] = useState<MingHistoryTurnItem[]>([]);
  const [listLoading, setListLoading] = useState(true);
  const [listError, setListError] = useState('');
  const [selectedTurn, setSelectedTurn] = useState<number | null>(null);
  const [detail, setDetail] = useState<MingHistoryDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  useEffect(() => {
    let alive = true;
    void mingFetchHistoryTurns()
      .then(({ turns: list }) => {
        if (!alive) return;
        setTurns(list || []);
        if (list?.length) setSelectedTurn(list[list.length - 1].turn);
      })
      .catch((e) => {
        if (alive) setListError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (alive) setListLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (selectedTurn == null) return;
    let alive = true;
    setDetailLoading(true);
    setDetailError('');
    void mingFetchHistoryTurn(selectedTurn)
      .then((d) => {
        if (alive) setDetail(d);
      })
      .catch((e) => {
        if (alive) setDetailError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (alive) setDetailLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [selectedTurn]);

  return (
    <MingFullscreenModal
      wide
      title="史册：历代奏报与诏书"
      subtitle={turns.length ? `共 ${turns.length} 月存档` : '尚无存档'}
      onClose={onClose}
    >
      <div style={{ display: 'flex', gap: 16, minHeight: 360 }}>
        <aside style={{ width: 200, flexShrink: 0, borderRight: '1px solid rgba(255,215,0,0.15)', paddingRight: 12 }}>
          {listLoading && <p style={{ fontSize: 12, color: '#aaa' }}>加载中…</p>}
          {listError && <p style={{ fontSize: 12, color: '#e57373' }}>{listError}</p>}
          {!listLoading && !listError && turns.length === 0 && (
            <p style={{ fontSize: 12, color: '#888' }}>尚无存档回合。</p>
          )}
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {turns
              .slice()
              .reverse()
              .map((t) => {
                const active = t.turn === selectedTurn;
                const tags: string[] = [];
                if (t.has_report) tags.push('奏报');
                if (t.has_directive) tags.push('诏');
                if (t.has_extraction) tags.push('册');
                return (
                  <li key={t.turn} style={{ marginBottom: 6 }}>
                    <button
                      type="button"
                      style={{
                        width: '100%',
                        textAlign: 'left',
                        padding: 8,
                        borderRadius: 6,
                        border: active ? '1px solid rgba(255,215,0,0.7)' : '1px solid rgba(255,215,0,0.15)',
                        background: active ? 'rgba(255,215,0,0.1)' : 'rgba(0,0,0,0.25)',
                        color: '#f5f5f5',
                        cursor: 'pointer',
                        fontSize: 12,
                      }}
                      onClick={() => setSelectedTurn(t.turn)}
                    >
                      <b>{t.year} 年 {t.period} 月</b>
                      <div style={{ color: '#888', marginTop: 2 }}>
                        第 {t.turn} 回合 · {tags.join(' / ') || '—'}
                      </div>
                    </button>
                  </li>
                );
              })}
          </ul>
        </aside>
        <article style={{ flex: 1, minWidth: 0 }}>
          {selectedTurn == null ? (
            <p style={{ color: '#888' }}>请从左侧择月。</p>
          ) : detailLoading ? (
            <p style={{ color: '#aaa' }}>加载中…</p>
          ) : detailError ? (
            <p style={{ color: '#e57373' }}>{detailError}</p>
          ) : !detail || !detail.exists ? (
            <p style={{ color: '#888' }}>该回合无存档。</p>
          ) : (
            <>
              {detail.decree_text && (
                <section style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>本月诏书</h3>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#ccc', lineHeight: 1.6 }}>
                    {detail.decree_text}
                  </pre>
                </section>
              )}
              {detail.report && (
                <section style={{ marginBottom: 16 }}>
                  <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>月末奏报</h3>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: 12, color: '#ccc', lineHeight: 1.6 }}>
                    {formatMingDetailNarrative(detail.report)}
                  </pre>
                </section>
              )}
              {detail.extraction && (
                <section>
                  <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>账目明细</h3>
                  <MingExtractionView data={detail.extraction} loading={false} error="" />
                </section>
              )}
            </>
          )}
        </article>
      </div>
    </MingFullscreenModal>
  );
};
