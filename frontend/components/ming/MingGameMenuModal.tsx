'use client';

import React, { useCallback, useEffect, useState } from 'react';
import type { MingGameSettings, MingLlmConfig, MingSaveEntry } from '../../game/ming/mingTurnPhase';
import {
  mingCreateSave,
  mingDeleteSave,
  mingFetchGameSettings,
  mingFetchLlmConfig,
  mingFetchSaves,
  mingMenuShutdown,
  mingSaveGameSettings,
  mingSaveLlmConfig,
} from '../../lib/mingApi';
import { useMingStore } from '../../game/ming/mingStore';
import { MingFullscreenModal } from './MingFullscreenModal';
import { mingOutlineBtn, mingPrimaryBtn } from '../../game/ming/mingUiStyles';

type Tab = 'save' | 'load' | 'llm' | 'settings' | 'reset' | 'exit_menu' | 'shutdown';

type Props = {
  onClose: () => void;
  onAfterLoad: () => void;
  onExitToMenu: () => void | Promise<void>;
};

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: '8px 12px',
  borderRadius: 6,
  border: active ? '1px solid rgba(255,215,0,0.7)' : '1px solid rgba(255,215,0,0.2)',
  background: active ? 'rgba(255,215,0,0.12)' : 'rgba(0,0,0,0.25)',
  color: active ? '#ffd700' : '#ccc',
  cursor: 'pointer',
  fontSize: 12,
  textAlign: 'left',
});

const fieldStyle: React.CSSProperties = {
  width: '100%',
  padding: 8,
  marginBottom: 10,
  borderRadius: 6,
  border: '1px solid rgba(255,215,0,0.25)',
  background: 'rgba(0,0,0,0.35)',
  color: '#f5f5f5',
  fontSize: 13,
};

function SavesList({
  saves,
  onRefresh,
  onLoad,
  loadBusy,
}: {
  saves: MingSaveEntry[];
  onRefresh: () => void;
  onLoad?: (name: string) => void;
  loadBusy?: string;
}) {
  const [delErr, setDelErr] = useState('');
  const onDelete = async (name: string) => {
    if (!window.confirm(`删除存档 ${name}.db？`)) return;
    try {
      await mingDeleteSave(name);
      onRefresh();
    } catch (e) {
      setDelErr(e instanceof Error ? e.message : String(e));
    }
  };
  if (!saves.length) return <p style={{ color: '#888', fontSize: 13 }}>尚无存档。</p>;
  return (
    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
      {delErr && <p style={{ color: '#f5222d', fontSize: 12 }}>{delErr}</p>}
      {saves.map((s) => (
        <li
          key={s.name}
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 8,
            padding: '8px 0',
            borderBottom: '1px solid rgba(255,215,0,0.1)',
          }}
        >
          <div>
            <b style={{ color: '#ffe7a3' }}>{s.label || s.name}</b>
            <div style={{ fontSize: 11, color: '#888' }}>
              {s.label && s.label !== s.name ? `${s.name} · ` : ''}
              {new Date(s.mtime * 1000).toLocaleString()} · {(s.size / 1024).toFixed(1)} KB
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {onLoad && (
              <button type="button" style={mingPrimaryBtn} disabled={loadBusy === s.name} onClick={() => onLoad(s.name)}>
                {loadBusy === s.name ? '加载中…' : '加载'}
              </button>
            )}
            <button type="button" style={mingOutlineBtn} onClick={() => void onDelete(s.name)}>删</button>
          </div>
        </li>
      ))}
    </ul>
  );
}

export const MingGameMenuModal: React.FC<Props> = ({ onClose, onAfterLoad, onExitToMenu }) => {
  const [tab, setTab] = useState<Tab>('save');

  return (
    <MingFullscreenModal wide title="游戏菜单" subtitle="存档、配置与系统" onClose={onClose}>
      <div style={{ display: 'flex', gap: 16, minHeight: 360 }}>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 6, minWidth: 140 }}>
          {(
            [
              ['save', '保存存档'],
              ['load', '加载存档'],
              ['llm', 'LLM 配置'],
              ['settings', '玩法设置'],
              ['reset', '重开新局'],
              ['exit_menu', '回到主菜单'],
              ['shutdown', '退出游戏'],
            ] as [Tab, string][]
          ).map(([key, label]) => (
            <button key={key} type="button" style={tabBtn(tab === key)} onClick={() => setTab(key)}>
              {label}
            </button>
          ))}
        </nav>
        <div style={{ flex: 1, minWidth: 0 }}>
          {tab === 'save' && <SaveTab />}
          {tab === 'load' && <LoadTab onAfterLoad={onAfterLoad} />}
          {tab === 'llm' && <LlmTab />}
          {tab === 'settings' && <SettingsTab />}
          {tab === 'reset' && <ResetTab onAfterReset={onAfterLoad} />}
          {tab === 'exit_menu' && <ExitTab onExit={onExitToMenu} />}
          {tab === 'shutdown' && <ShutdownTab />}
        </div>
      </div>
    </MingFullscreenModal>
  );
};

function SaveTab() {
  const [name, setName] = useState('');
  const [saves, setSaves] = useState<MingSaveEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  const refresh = useCallback(async () => {
    try {
      const data = await mingFetchSaves();
      setSaves(data.saves);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  const onSave = async () => {
    if (!name.trim()) {
      setErr('请填存档名。');
      return;
    }
    setBusy(true);
    setErr('');
    setMsg('');
    try {
      await mingCreateSave(name.trim());
      setMsg(`已保存为 ${name.trim()}.db`);
      setName('');
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>保存当前局</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>热备到 data/saves/&lt;名字&gt;.db，同名覆盖。</p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <input className="" style={fieldStyle} placeholder="存档名" value={name} onChange={(e) => setName(e.target.value)} disabled={busy} />
        <button type="button" style={mingPrimaryBtn} onClick={() => void onSave()} disabled={busy}>{busy ? '保存中…' : '保存'}</button>
      </div>
      {msg && <p style={{ color: '#52c41a', fontSize: 12 }}>{msg}</p>}
      {err && <p style={{ color: '#f5222d', fontSize: 12 }}>{err}</p>}
      <h4 style={{ color: '#d4af37', margin: '16px 0 8px' }}>现有存档</h4>
      <SavesList saves={saves} onRefresh={() => void refresh()} />
    </section>
  );
}

function LoadTab({ onAfterLoad }: { onAfterLoad: () => void }) {
  const loadSave = useMingStore((s) => s.loadSave);
  const [saves, setSaves] = useState<MingSaveEntry[]>([]);
  const [busy, setBusy] = useState('');
  const [err, setErr] = useState('');
  const refresh = useCallback(async () => {
    try {
      const data = await mingFetchSaves();
      setSaves(data.saves);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  const onLoad = async (n: string) => {
    if (!window.confirm(`确定加载 ${n}.db？当前未保存进度会丢失。`)) return;
    setBusy(n);
    setErr('');
    try {
      await loadSave(n);
      onAfterLoad();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy('');
    }
  };
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>加载存档</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>覆盖主 DB 并刷新当前界面。</p>
      {err && <p style={{ color: '#f5222d', fontSize: 12 }}>{err}</p>}
      <SavesList saves={saves} onRefresh={() => void refresh()} onLoad={(n) => void onLoad(n)} loadBusy={busy} />
    </section>
  );
}

function LlmTab() {
  const [info, setInfo] = useState<MingLlmConfig | null>(null);
  const [baseUrl, setBaseUrl] = useState('');
  const [model, setModel] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [maxTokens, setMaxTokens] = useState('8000');
  const [thinkingLevel, setThinkingLevel] = useState('');
  const [advancedModel, setAdvancedModel] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  useEffect(() => {
    mingFetchLlmConfig()
      .then((data) => {
        setInfo(data);
        setBaseUrl(data.base_url);
        setModel(data.model);
        setAdvancedModel(data.advanced_model || '');
        setMaxTokens(String(data.max_tokens || 8000));
        setThinkingLevel(data.thinking_level || '');
      })
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);
  const onSave = async () => {
    setBusy(true);
    setErr('');
    setMsg('');
    try {
      const data = await mingSaveLlmConfig({
        base_url: baseUrl,
        model,
        api_key: apiKey,
        max_tokens: parseInt(maxTokens, 10) || 8000,
        thinking_level: thinkingLevel.trim(),
        advanced_model: advancedModel,
        advanced_base_url: info?.advanced_base_url || '',
        advanced_api_key: '__keep__',
        advanced_thinking_level: info?.advanced_thinking_level || '',
        timeout_seconds: info?.timeout_seconds || 180,
        connect_timeout_seconds: info?.connect_timeout_seconds || 60,
        read_timeout_seconds: info?.read_timeout_seconds || 120,
      });
      setInfo(data);
      setApiKey('');
      setMsg('已生效并写入 runtime_llm.json。');
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>LLM 配置</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>立即生效。API Key 留空则保留当前。</p>
      <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>Base URL</label>
      <input style={fieldStyle} value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>Model</label>
      <input style={fieldStyle} value={model} onChange={(e) => setModel(e.target.value)} />
      <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>Advanced Model</label>
      <input style={fieldStyle} value={advancedModel} onChange={(e) => setAdvancedModel(e.target.value)} placeholder="推演专用，空=与 Model 一致" />
      <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>Thinking Level</label>
      <input style={fieldStyle} value={thinkingLevel} onChange={(e) => setThinkingLevel(e.target.value)} placeholder="空=默认" />
      <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>
        API Key {info?.has_api_key ? <span style={{ color: '#52c41a' }}>（已设置）</span> : null}
      </label>
      <input style={fieldStyle} type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} placeholder="留空保留当前" />
      <label style={{ display: 'block', fontSize: 12, color: '#aaa', marginBottom: 4 }}>Max Tokens</label>
      <input style={fieldStyle} type="number" value={maxTokens} onChange={(e) => setMaxTokens(e.target.value)} />
      <button type="button" style={mingPrimaryBtn} onClick={() => void onSave()} disabled={busy}>{busy ? '保存中…' : '保存并应用'}</button>
      {msg && <p style={{ color: '#52c41a', fontSize: 12, marginTop: 8 }}>{msg}</p>}
      {err && <p style={{ color: '#f5222d', fontSize: 12, marginTop: 8 }}>{err}</p>}
    </section>
  );
}

function SettingsTab() {
  const setCourtChatStreamSpeed = useMingStore((s) => s.setCourtChatStreamSpeed);
  const [settings, setSettings] = useState<MingGameSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [err, setErr] = useState('');
  useEffect(() => {
    mingFetchGameSettings()
      .then((data) => setSettings(data.game_settings))
      .catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);
  const onSave = async () => {
    if (!settings) return;
    setBusy(true);
    setErr('');
    setMsg('');
    try {
      const out = await mingSaveGameSettings(settings);
      setSettings(out.game_settings);
      const speed = Number(out.game_settings.court_chat_stream_speed);
      if (Number.isFinite(speed)) setCourtChatStreamSpeed(speed, false);
      setMsg('玩法设置已保存。');
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  if (!settings) return <p style={{ color: '#888' }}>{err || '加载中…'}</p>;
  const fields: Array<{ key: keyof MingGameSettings; label: string; min?: number; max?: number }> = [
    { key: 'hitl_min_decisions', label: 'HITL 最少决策点', min: 0, max: 5 },
    { key: 'court_chat_debate_rounds', label: '廷议交锋轮数', min: 1, max: 8 },
    { key: 'court_chat_stream_speed', label: '廷议流式语速 (1慢–5快)', min: 1, max: 5 },
    { key: 'max_decree_issues', label: '诏书同时局势上限', min: 1, max: 30 },
    { key: 'issue_log_limit', label: '局势日志条数', min: 0, max: 20 },
    { key: 'secret_order_person_limit', label: '单人密令上限', min: 1, max: 10 },
    { key: 'secret_order_total_limit', label: '全朝密令上限', min: 1, max: 20 },
    { key: 'character_limit', label: '朝臣建档上限', min: 20, max: 300 },
  ];
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>玩法设置</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>写入 runtime_game.json，下一回合推演生效。</p>
      {fields.map((f) => (
        <label key={f.key} style={{ display: 'block', marginBottom: 10 }}>
          <span style={{ fontSize: 12, color: '#aaa' }}>{f.label}</span>
          <input
            style={fieldStyle}
            type="number"
            min={f.min}
            max={f.max}
            value={settings[f.key]}
            onChange={(e) =>
              setSettings({ ...settings, [f.key]: Number(e.target.value) })
            }
          />
        </label>
      ))}
      <button type="button" style={mingPrimaryBtn} onClick={() => void onSave()} disabled={busy}>{busy ? '保存中…' : '保存设置'}</button>
      {msg && <p style={{ color: '#52c41a', fontSize: 12, marginTop: 8 }}>{msg}</p>}
      {err && <p style={{ color: '#f5222d', fontSize: 12, marginTop: 8 }}>{err}</p>}
    </section>
  );
}

function ResetTab({ onAfterReset }: { onAfterReset: () => void }) {
  const resetGame = useMingStore((s) => s.resetGame);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const canReset = confirmText.trim() === '重开';
  const onReset = async () => {
    if (!canReset) return;
    if (!window.confirm('确定重开新局？当前局数据将永久清空（存档目录不动）。')) return;
    setBusy(true);
    setErr('');
    try {
      await resetGame();
      onAfterReset();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>重开新局</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>清空主 DB，不可撤销。请先保存存档。</p>
      <div style={{ display: 'flex', gap: 8 }}>
        <input style={fieldStyle} placeholder="输入：重开" value={confirmText} onChange={(e) => setConfirmText(e.target.value)} disabled={busy} />
        <button type="button" style={{ ...mingPrimaryBtn, background: '#a61e1e' }} onClick={() => void onReset()} disabled={!canReset || busy}>
          {busy ? '重开中…' : '重开新局'}
        </button>
      </div>
      {err && <p style={{ color: '#f5222d', fontSize: 12 }}>{err}</p>}
    </section>
  );
}

function ExitTab({ onExit }: { onExit: () => void | Promise<void> }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const onClick = async () => {
    if (!window.confirm('回到主菜单？当前对局会关闭，可从「继续上局」回来。')) return;
    setBusy(true);
    setErr('');
    try {
      await onExit();
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>回到主菜单</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>关闭会话，数据库与存档保留。</p>
      <button type="button" style={mingPrimaryBtn} onClick={() => void onClick()} disabled={busy}>
        {busy ? '处理中…' : '回到主菜单'}
      </button>
      {err && <p style={{ color: '#f5222d', fontSize: 12 }}>{err}</p>}
    </section>
  );
}

function ShutdownTab() {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const onClick = async () => {
    if (!window.confirm('退出整个游戏？服务进程将关闭。')) return;
    setBusy(true);
    setErr('');
    try {
      await mingMenuShutdown();
      setTimeout(() => {
        try {
          window.close();
        } catch {
          /* noop */
        }
      }, 400);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };
  return (
    <section>
      <h3 style={{ margin: '0 0 8px', color: '#ffe7a3' }}>退出游戏</h3>
      <p style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>终止服务进程。未保存进度会丢失。</p>
      <button type="button" style={{ ...mingPrimaryBtn, background: '#a61e1e' }} onClick={() => void onClick()} disabled={busy}>
        {busy ? '退出中…' : '退出游戏'}
      </button>
      {err && <p style={{ color: '#f5222d', fontSize: 12 }}>{err}</p>}
    </section>
  );
}
