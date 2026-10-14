'use client';

import React, { useEffect, useState } from 'react';
import { MingFullscreenModal } from './MingFullscreenModal';
import { mingDeleteSecretOrder, mingFetchSecretOrders } from '../../lib/mingApi';
import type { MingSecretOrder } from '../../game/ming/mingTurnPhase';
import { mingOutlineBtn } from '../../game/ming/mingUiStyles';

type Tab = 'active' | 'pending_review' | 'done' | 'failed' | 'all';

const STATUS_LABEL: Record<string, string> = {
  active: '进行中',
  pending_review: '待核议',
  done: '已完成',
  failed: '已失败',
  cancelled: '已撤销',
};

type Props = {
  onClose: () => void;
  onOpenMinister?: (name: string) => void;
};

export const MingSecretOrdersModal: React.FC<Props> = ({ onClose, onOpenMinister }) => {
  const [orders, setOrders] = useState<MingSecretOrder[]>([]);
  const [tab, setTab] = useState<Tab>('active');
  const [selected, setSelected] = useState<MingSecretOrder | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let alive = true;
    void mingFetchSecretOrders()
      .then(({ orders: list }) => {
        if (alive) setOrders(list || []);
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

  const visible = tab === 'all' ? orders : orders.filter((o) => o.status === tab);

  const handleDelete = async (order: MingSecretOrder) => {
    if (!window.confirm(`确定删除密令〔${order.title}〕？`)) return;
    try {
      await mingDeleteSecretOrder(order.id);
      const { orders: list } = await mingFetchSecretOrders();
      setOrders(list || []);
      if (selected?.id === order.id) setSelected(null);
    } catch (e) {
      window.alert(e instanceof Error ? e.message : '删除失败');
    }
  };

  if (selected) {
    return (
      <MingFullscreenModal
        title={selected.title}
        subtitle={`承办：${selected.minister_name} · ${STATUS_LABEL[selected.status] || selected.status}`}
        onClose={() => setSelected(null)}
      >
        <p style={{ fontSize: 12, color: '#999', marginBottom: 12 }}>
          第 {selected.year_issued} 年 {selected.period_issued} 月下令
        </p>
        <pre style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.7, color: '#ddd' }}>
          {selected.content}
        </pre>
        {selected.result && (
          <div style={{ marginTop: 12, padding: 10, borderRadius: 8, background: 'rgba(0,0,0,0.3)' }}>
            <div style={{ color: '#ffd700', fontSize: 12, marginBottom: 4 }}>结果</div>
            <div style={{ fontSize: 13, color: '#ccc' }}>{selected.result}</div>
          </div>
        )}
        {selected.sim_note && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#888' }}>推演备注：{selected.sim_note}</div>
        )}
        <div style={{ display: 'flex', gap: 8, marginTop: 16, flexWrap: 'wrap' }}>
          {onOpenMinister && (
            <button type="button" style={mingOutlineBtn} onClick={() => onOpenMinister(selected.minister_name)}>
              召见承办人
            </button>
          )}
          <button type="button" style={mingOutlineBtn} onClick={() => void handleDelete(selected)}>
            删除密令
          </button>
        </div>
      </MingFullscreenModal>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'active', label: `进行中 (${orders.filter((o) => o.status === 'active').length})` },
    { key: 'pending_review', label: `待核议 (${orders.filter((o) => o.status === 'pending_review').length})` },
    { key: 'done', label: `已完成 (${orders.filter((o) => o.status === 'done').length})` },
    { key: 'failed', label: `已失败 (${orders.filter((o) => o.status === 'failed').length})` },
    { key: 'all', label: `全部 (${orders.length})` },
  ];

  return (
    <MingFullscreenModal title="密令进度" subtitle={`共 ${orders.length} 条密令记录`} onClose={onClose}>
      {loading && <p style={{ color: '#aaa' }}>加载中…</p>}
      {error && <p style={{ color: '#e57373' }}>{error}</p>}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            style={{
              ...mingOutlineBtn,
              borderColor: tab === t.key ? 'rgba(255,215,0,0.8)' : 'rgba(255,215,0,0.25)',
              fontSize: 11,
            }}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {visible.length === 0 ? (
        <p style={{ color: '#888', fontSize: 13 }}>暂无此类密令。</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
          {visible.map((o) => (
            <li key={o.id} style={{ marginBottom: 8 }}>
              <button
                type="button"
                style={{
                  width: '100%',
                  textAlign: 'left',
                  padding: 10,
                  borderRadius: 8,
                  border: '1px solid rgba(255,215,0,0.2)',
                  background: 'rgba(0,0,0,0.3)',
                  color: '#f5f5f5',
                  cursor: 'pointer',
                }}
                onClick={() => setSelected(o)}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <b style={{ color: '#ffe7a3' }}>{o.title}</b>
                  <span style={{ fontSize: 11, color: '#d4af37' }}>
                    {STATUS_LABEL[o.status] || o.status}
                  </span>
                </div>
                <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
                  第 {o.year_issued} 年 {o.period_issued} 月 · 承办：{o.minister_name}
                </div>
              </button>
            </li>
          ))}
        </ul>
      )}
    </MingFullscreenModal>
  );
};
