'use client';

import React from 'react';
import type { MingClosedIssue } from '../../game/ming/mingTurnPhase';
import { MingFullscreenModal } from './MingFullscreenModal';
import { formatMingClosedEffect } from '../../game/ming/mingSituationFormat';

type Props = {
  items: MingClosedIssue[];
  onClose: () => void;
};

export const MingClosedIssuesModal: React.FC<Props> = ({ items, onClose }) => {
  const resolved = items.filter((i) => i.status === 'resolved');
  const failed = items.filter((i) => i.status === 'failed');
  const dropped = items.filter((i) => i.status === 'dropped');

  const Group = ({
    title,
    list,
    cls,
  }: {
    title: string;
    list: MingClosedIssue[];
    cls: string;
  }) =>
    list.length ? (
      <section style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, color: cls === 'resolved' ? '#4caf50' : cls === 'failed' ? '#e57373' : '#ffb74d', marginBottom: 8 }}>
          {title}
        </h3>
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {list.map((it) => (
            <li
              key={it.id}
              style={{
                marginBottom: 10,
                padding: 10,
                borderRadius: 8,
                border: '1px solid rgba(255,215,0,0.15)',
                background: 'rgba(0,0,0,0.25)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, marginBottom: 4 }}>
                <b style={{ color: '#ffe7a3' }}>#{it.id} {it.title}</b>
                <span style={{ fontSize: 11, color: '#888' }}>
                  {cls === 'resolved' ? it.bar_good_meaning : it.bar_bad_meaning}
                </span>
              </div>
              {it.stage_text && (
                <p style={{ fontSize: 12, color: '#aaa', margin: '4px 0' }}>{it.stage_text}</p>
              )}
              <div style={{ fontSize: 12, color: '#bbb' }}>{formatMingClosedEffect(it.effect)}</div>
            </li>
          ))}
        </ul>
      </section>
    ) : null;

  return (
    <MingFullscreenModal
      title="局势了结"
      subtitle={`本月共 ${items.length} 条局势了结`}
      onClose={onClose}
    >
      <Group title="已结案" list={resolved} cls="resolved" />
      <Group title="已崩坏" list={failed} cls="failed" />
      <Group title="已撤旨" list={dropped} cls="dropped" />
    </MingFullscreenModal>
  );
};
