'use client';

import React, { useRef } from 'react';
import type { SalvageMinister } from '../../../game/ming/salvageStateTypes';
import { MingDrawerShell, drawerRowStyle, drawerSearchStyle } from './MingDrawerShell';
import { mingOutlineBtn } from '../../../game/ming/mingUiStyles';

type Props = {
  open: boolean;
  consorts: SalvageMinister[];
  candidates?: SalvageMinister[];
  onOpenChat?: (name: string) => void;
  onUploadPortrait?: (name: string, file: File) => Promise<void>;
  onSelectCandidate?: (name: string) => Promise<void>;
  onClose: () => void;
};

export const MingHaremDrawer: React.FC<Props> = ({
  open,
  consorts,
  candidates = [],
  onOpenChat,
  onUploadPortrait,
  onSelectCandidate,
  onClose,
}) => {
  const [q, setQ] = React.useState('');
  const [group, setGroup] = React.useState<'全部' | '收藏'>('全部');
  const [busy, setBusy] = React.useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const uploadTargetRef = useRef<string>('');

  const rows = React.useMemo(() => {
    let list = consorts.filter((c) => c.status === 'active');
    if (group === '收藏') list = list.filter((c) => c.favorite);
    if (!q.trim()) return list;
    const needle = q.trim();
    return list.filter((c) => c.name.includes(needle) || (c.office || '').includes(needle));
  }, [consorts, group, q]);

  const pickPortrait = (name: string) => {
    uploadTargetRef.current = name;
    fileRef.current?.click();
  };

  const onFile = async (file: File) => {
    const name = uploadTargetRef.current;
    if (!name || !onUploadPortrait) return;
    setBusy(name);
    try {
      await onUploadPortrait(name, file);
    } finally {
      setBusy('');
      uploadTargetRef.current = '';
    }
  };

  return (
    <MingDrawerShell open={open} title="后宫" subtitle="妃嫔名册" onClose={onClose}>
      {candidates.length > 0 && onSelectCandidate ? (
        <div
          style={{
            marginBottom: 12,
            padding: 10,
            borderRadius: 8,
            border: '1px solid rgba(255,183,77,0.35)',
            background: 'rgba(255,183,77,0.08)',
          }}
        >
          <div style={{ fontSize: 12, color: '#ffb74d', marginBottom: 8, fontWeight: 600 }}>待选秀女</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {candidates.map((c) => (
              <button
                key={c.name}
                type="button"
                disabled={busy === c.name}
                style={{ ...mingOutlineBtn, fontSize: 11 }}
                onClick={() => {
                  setBusy(c.name);
                  void onSelectCandidate(c.name).finally(() => setBusy(''));
                }}
              >
                {busy === c.name ? '…' : `选 ${c.name}`}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div style={{ display: 'flex', gap: 6, marginBottom: 10 }}>
        {(['全部', '收藏'] as const).map((g) => (
          <button
            key={g}
            type="button"
            onClick={() => setGroup(g)}
            style={{
              flex: 1,
              padding: '6px 8px',
              borderRadius: 6,
              border: group === g ? '1px solid rgba(255,215,0,0.75)' : '1px solid rgba(255,255,255,0.1)',
              background: group === g ? 'rgba(255,215,0,0.12)' : 'transparent',
              color: group === g ? '#ffd700' : '#aaa',
              cursor: 'pointer',
            }}
          >
            {g}
          </button>
        ))}
      </div>
      <input
        style={drawerSearchStyle}
        placeholder="搜索妃嫔…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onFile(f);
          e.target.value = '';
        }}
      />
      {rows.map((c) => (
        <div key={c.name} style={{ marginBottom: 8 }}>
          <button
            type="button"
            style={drawerRowStyle(false)}
            onClick={() => {
              onOpenChat?.(c.name);
              onClose();
            }}
            disabled={!onOpenChat}
          >
            <div style={{ fontWeight: 600 }}>
              {c.name}
              {c.favorite && <span style={{ color: '#ffd700', marginLeft: 4 }}>★</span>}
            </div>
            <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>{c.office || '妃嫔'}</div>
            {c.summary && (
              <div style={{ fontSize: 11, color: '#777', marginTop: 4, lineHeight: 1.5 }}>{c.summary}</div>
            )}
          </button>
          {onUploadPortrait ? (
            <button
              type="button"
              style={{ ...mingOutlineBtn, fontSize: 10, marginTop: 4, padding: '2px 8px' }}
              disabled={busy === c.name}
              onClick={() => pickPortrait(c.name)}
            >
              {busy === c.name ? '上传中…' : '换立绘'}
            </button>
          ) : null}
        </div>
      ))}
      {!rows.length && <p style={{ color: '#888', fontSize: 13 }}>暂无妃嫔记录。</p>}
    </MingDrawerShell>
  );
};
