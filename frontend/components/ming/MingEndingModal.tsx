'use client';

import React from 'react';
import type { ScenarioId } from '../../game/scenarios';
import type { MingEnding } from '../../game/ming/mingTurnPhase';
import { getEndingUiCopy } from '../../game/ming/mingEndingUi';
import { MingFullscreenModal } from './MingFullscreenModal';
import { mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Props = {
  ending: MingEnding;
  scenarioId?: ScenarioId | string;
  onClose: () => void;
  onBackToMenu?: () => void;
};

export const MingEndingModal: React.FC<Props> = ({ ending, scenarioId, onClose, onBackToMenu }) => {
  const copy = getEndingUiCopy(scenarioId);
  const last = ending.timeline?.[ending.timeline.length - 1];
  const endingDate = last ? `${last.year}年${last.period}月` : '终局';
  const timelineCount = ending.timeline?.length ?? 0;

  return (
    <MingFullscreenModal
      wide
      title="终章定论"
      subtitle={`${copy.chronicleSubtitle} · ${endingDate}`}
      onClose={onClose}
    >
      <div
        style={{
          marginBottom: 20,
          padding: 16,
          borderRadius: 10,
          border: '1px solid rgba(255,215,0,0.35)',
          background: 'rgba(255,215,0,0.06)',
          textAlign: 'center',
        }}
      >
        <p style={{ margin: 0, fontSize: 12, color: '#aaa' }}>{copy.reviewerLabel}</p>
        <h2 style={{ margin: '8px 0 4px', fontSize: 22, color: '#ffe7a3' }}>{ending.label}</h2>
        <span style={{ fontSize: 12, color: '#888' }}>第 {timelineCount || 1} 卷</span>
      </div>

      {ending.summary && (
        <section style={{ marginBottom: 20 }}>
          <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 8 }}>{copy.summaryHeading}</h3>
          <pre
            style={{
              whiteSpace: 'pre-wrap',
              fontSize: 13,
              lineHeight: 1.75,
              color: '#ccc',
              fontFamily: 'inherit',
              margin: 0,
            }}
          >
            {ending.summary}
          </pre>
        </section>
      )}

      {ending.timeline && ending.timeline.length > 0 && (
        <section>
          <h3 style={{ fontSize: 13, color: '#ffd700', marginBottom: 10 }}>{copy.timelineHeading}</h3>
          <ol style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {ending.timeline.map((it) => (
              <li
                key={it.turn}
                style={{
                  display: 'flex',
                  gap: 12,
                  marginBottom: 12,
                  padding: 10,
                  borderRadius: 8,
                  border: '1px solid rgba(255,215,0,0.12)',
                  background: 'rgba(0,0,0,0.25)',
                }}
              >
                <div style={{ flexShrink: 0, width: 72, textAlign: 'center' }}>
                  <b style={{ color: '#ffe7a3', fontSize: 14 }}>{it.year}</b>
                  <div style={{ fontSize: 11, color: '#888' }}>{it.period}月</div>
                </div>
                <div style={{ flex: 1, fontSize: 12, lineHeight: 1.6, color: '#bbb' }}>
                  {it.chapter && <p style={{ margin: '0 0 4px', color: '#ddd' }}>{it.chapter}</p>}
                  {it.decree_brief && (
                    <p style={{ margin: '0 0 4px', color: '#c9a227' }}>诏：{it.decree_brief}</p>
                  )}
                  {it.effect_brief && <p style={{ margin: 0, color: '#999' }}>效：{it.effect_brief}</p>}
                </div>
              </li>
            ))}
          </ol>
        </section>
      )}

      {onBackToMenu && (
        <div style={{ marginTop: 20, textAlign: 'center' }}>
          <button type="button" style={mingPrimaryBtn} onClick={onBackToMenu}>
            返回选剧本
          </button>
        </div>
      )}
    </MingFullscreenModal>
  );
};
