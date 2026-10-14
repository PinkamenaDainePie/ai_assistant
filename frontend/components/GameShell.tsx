import React, { useEffect, useMemo, useState } from 'react';
import { TopStatusBar } from './TopStatusBar';
import { LeftActionNav } from './LeftActionNav';
import { MapScenePanel } from './MapScenePanel';
import { TaskPanel } from './TaskPanel';
import { EdictComposerPanel } from './EdictComposerPanel';
import { RightActionBar } from './RightActionBar';
import { EdgeDockRail } from './EdgeDockRail';
import { AIDialogPanel } from './AIDialogPanel';
import { MemorialListDrawer } from './MemorialListDrawer';
import { TimelineLog } from './TimelineLog';
import { useGameStore, computeSkillWalletRemaining } from '../game/store';
import { useMingStore } from '../game/ming/mingStore';
import { isSalvageSessionPersisted } from '../game/ming/mingSessionStorage';
import { isSalvageScenario, type ScenarioId } from '../game/scenarios';
import { MingGameShell } from './ming/MingGameShell';
import { MingMenuHome } from './ming/MingMenuHome';
import {
  formatCurrentPoolLine,
  formatTaskSettlementLine,
} from '../game/settlementSummary';
import { ScenarioHomePanel } from './ScenarioHomePanel';
import { CoursePortalHome } from './portal/CoursePortalHome';
import { QuarterReportModal } from './QuarterReportModal';
import { QuarterChapterDetailModal } from './QuarterChapterDetailModal';
import { formatQuarterReportForDisplay } from '../game/quarterReportDisplay';
import { resolveQuarterChapterDetail } from '../game/quarterChapterDisplay';
import { formatAgentFlowReport } from '../game/agentFlowDisplay';
import { EndingReportTables } from './EndingReportTables';
import { NextQuarterProgressOverlay, StartGameProgressOverlay } from './ActionProgressBar';

export const GameShell: React.FC = () => {
  const [showLeftRail, setShowLeftRail] = useState(false);
  const [showRightRail, setShowRightRail] = useState(false);
  const [homeView, setHomeView] = useState<'portal' | 'game'>('portal');
  const [salvageMenuOpen, setSalvageMenuOpen] = useState(false);
  const mingActive = useMingStore((s) => s.active);
  const mingLoading = useMingStore((s) => s.loading);
  const mingError = useMingStore((s) => s.error);
  const clearMingError = useMingStore((s) => s.clearError);
  const restoreMingSession = useMingStore((s) => s.restoreSession);
  const canContinueSalvageScenario = useMingStore((s) => s.canContinueSalvageScenario);
  const setActiveSalvageScenarioId = useMingStore((s) => s.setActiveSalvageScenarioId);
  const activeSalvageScenarioId = useMingStore((s) => s.activeSalvageScenarioId);
  const fetchMingMenuBootstrap = useMingStore((s) => s.fetchMenuBootstrap);
  const handleMingContinueGame = useMingStore((s) => s.handleContinueGame);
  const handleMingStartGame = useMingStore((s) => s.handleStartGame);

  useEffect(() => {
    if (mingActive) setSalvageMenuOpen(false);
  }, [mingActive]);

  useEffect(() => {
    if (mingActive) return;
    if (!isSalvageSessionPersisted()) return;
    void restoreMingSession().then((ok) => {
      if (ok) setHomeView('game');
    });
  }, [mingActive, restoreMingSession]);

  const {
    gamePhase,
    loading,
    loadingKind,
    error,
    clearError,
    scenarioId,
    setScenarioId,
    handleStartGame,
    events,
    currentEventIndex,
    handleSelectEventOption,
    selectedFocus,
    setSelectedFocus,
    handleSelectQuarterFocus,
    skillUi,
    skillSubmitEnabled,
    handleSwitchSkillTree,
    handleOpenSkillNodeDetail,
    handleAllocateSkillPoint,
    handleConfirmSkillAllocation,
    handleCancelSkillAllocation,
    settlement,
    currentQuarter,
    nationState,
    skillAllocBaseline,
    campaignEpilogue,
    campaignMilestonePrompt,
    handleCampaignMilestoneContinue,
    handleCampaignMilestoneEnd,
    handleExitToScenarioSelect,
    latestQuarterReport,
    ui,
    openQuarterReport,
    closeQuarterReport,
    quarterChapters,
    closeQuarterChapterDetail,
    campaignOpeningMetrics,
  } = useGameStore((s) => ({
    gamePhase: s.gamePhase,
    loading: s.loading,
    loadingKind: s.loadingKind,
    error: s.error,
    clearError: s.clearError,
    scenarioId: s.scenarioId,
    setScenarioId: s.setScenarioId,
    handleStartGame: s.handleStartGame,
    events: s.events,
    currentEventIndex: s.currentEventIndex,
    handleSelectEventOption: s.handleSelectEventOption,
    selectedFocus: s.selectedFocus,
    setSelectedFocus: s.setSelectedFocus,
    handleSelectQuarterFocus: s.handleSelectQuarterFocus,
    skillUi: s.skillUi,
    skillSubmitEnabled: s.skillSubmitEnabled,
    handleSwitchSkillTree: s.handleSwitchSkillTree,
    handleOpenSkillNodeDetail: s.handleOpenSkillNodeDetail,
    handleAllocateSkillPoint: s.handleAllocateSkillPoint,
    handleConfirmSkillAllocation: s.handleConfirmSkillAllocation,
    handleCancelSkillAllocation: s.handleCancelSkillAllocation,
    settlement: s.settlement,
    currentQuarter: s.currentQuarter,
    nationState: s.nationState,
    skillAllocBaseline: s.skillAllocBaseline,
    campaignEpilogue: s.campaignEpilogue,
    campaignMilestonePrompt: s.campaignMilestonePrompt,
    handleCampaignMilestoneContinue: s.handleCampaignMilestoneContinue,
    handleCampaignMilestoneEnd: s.handleCampaignMilestoneEnd,
    handleExitToScenarioSelect: s.handleExitToScenarioSelect,
    latestQuarterReport: s.latestQuarterReport,
    ui: s.ui,
    openQuarterReport: s.openQuarterReport,
    closeQuarterReport: s.closeQuarterReport,
    quarterChapters: s.quarterChapters,
    closeQuarterChapterDetail: s.closeQuarterChapterDetail,
    campaignOpeningMetrics: s.campaignOpeningMetrics,
  }));

  const railsDisabled = useMemo(() => {
    // 在全屏浮层（如诏书）或选剧本首页时，不需要边栏
    return gamePhase === 'DECREE_MODAL' || gamePhase === 'HOME';
  }, [gamePhase]);

  const isSalvageHome = isSalvageScenario(scenarioId);

  const scenarioHomeLoading = isSalvageHome ? mingLoading : loading;
  const scenarioHomeError = isSalvageHome ? mingError : error;
  const clearScenarioHomeError = isSalvageHome ? clearMingError : clearError;

  useEffect(() => {
    if (gamePhase !== 'HOME' || mingActive) return;
    void fetchMingMenuBootstrap();
  }, [gamePhase, mingActive, fetchMingMenuBootstrap]);

  const quarterChapterDetail = useMemo(
    () =>
      resolveQuarterChapterDetail(ui.selectedQuarterChapterId, quarterChapters, {
        scenarioId,
        currentQuarter,
        latestReport: latestQuarterReport,
      }),
    [ui.selectedQuarterChapterId, quarterChapters, scenarioId, currentQuarter, latestQuarterReport],
  );

  if (gamePhase === 'HOME' && homeView === 'portal') {
    return (
      <CoursePortalHome
        onEnterGame={() => {
          if (!scenarioId) {
            setScenarioId('song_xining_v2');
          }
          setHomeView('game');
        }}
      />
    );
  }

  if (mingActive) {
    return (
      <MingGameShell
        scenarioId={(activeSalvageScenarioId || scenarioId || 'ming_wanli') as ScenarioId}
        onBackToScenarioSelect={() => {
          useMingStore.getState().handleExit();
        }}
      />
    );
  }

  const quarterReportDisplay = formatQuarterReportForDisplay(latestQuarterReport, {
    currentQuarter,
    scenarioId,
  });

  const currentEvent = events[currentEventIndex];
  const focusOptions = [
    { key: 'military', label: '军事' },
    { key: 'management', label: '管理' },
    { key: 'politics', label: '政治' },
    { key: 'scholarship', label: '学识' },
  ];
  const settlementMetricRows = nationState.metrics.map((metric) => {
    const before = settlement?.baselineMetrics?.[metric.key] ?? metric.value;
    const after = settlement?.finalMetrics?.[metric.key] ?? metric.value;
    const delta = Number((after - before).toFixed(2));
    return {
      key: metric.key,
      label: metric.label,
      before: Number(before.toFixed(2)),
      after: Number(after.toFixed(2)),
      delta,
    };
  });
  const agentFlowDisplay = formatAgentFlowReport(settlement?.agentFlowReport);
  const skillTabs = [
    { key: 'military', label: '军事' },
    { key: 'management', label: '管理' },
    { key: 'scholarship', label: '学识' },
    { key: 'politics', label: '政治' },
  ] as const;
  const skillTabFocusSet =
    gamePhase === 'SKILL_ALLOCATION' && selectedFocus.length === 3 ? new Set(selectedFocus) : null;
  const activeSkillNodes = skillUi.skillTrees[skillUi.activeTree].nodes;
  const openSkillNode =
    activeSkillNodes.find((node) => node.id === skillUi.openNodeDetailId) ||
    undefined;
  const remainingWallet =
    gamePhase === 'SKILL_ALLOCATION'
      ? computeSkillWalletRemaining(skillUi, skillAllocBaseline)
      : (() => {
          const spentByTree = {
            military: skillUi.skillTrees.military.nodes.reduce((sum, node) => sum + node.currentLevel * node.cost, 0),
            management: skillUi.skillTrees.management.nodes.reduce((sum, node) => sum + node.currentLevel * node.cost, 0),
            politics: skillUi.skillTrees.politics.nodes.reduce((sum, node) => sum + node.currentLevel * node.cost, 0),
            scholarship: skillUi.skillTrees.scholarship.nodes.reduce((sum, node) => sum + node.currentLevel * node.cost, 0),
          };
          const base = { ...skillUi.pointWallet };
          (['military', 'management', 'politics', 'scholarship'] as const).forEach((tree) => {
            const treeBudget = Number(skillUi.pointWallet[tree] || 0);
            const spend = Number(spentByTree[tree] || 0);
            const consumeTree = Math.min(treeBudget, spend);
            const spill = Math.max(0, spend - consumeTree);
            base[tree] = Math.max(0, treeBudget - consumeTree);
            base.generic = Math.max(0, base.generic - spill);
          });
          return base;
        })();

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#050406',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <TopStatusBar
        onBack={gamePhase !== 'HOME' ? handleExitToScenarioSelect : undefined}
        backDisabled={loading}
      />
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {!railsDisabled && (
          <EdgeDockRail
            side="left"
            open={showLeftRail}
            onOpen={() => setShowLeftRail(true)}
            onClose={() => setShowLeftRail(false)}
          >
            <LeftActionNav />
          </EdgeDockRail>
        )}

        {!railsDisabled && (
          <EdgeDockRail
            side="right"
            open={showRightRail}
            onOpen={() => setShowRightRail(true)}
            onClose={() => setShowRightRail(false)}
          >
            <RightActionBar />
          </EdgeDockRail>
        )}

        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            isolation: 'isolate',
          }}
        >
          <MapScenePanel />
          <StartGameProgressOverlay active={loading && loadingKind === 'start_game'} />
          <NextQuarterProgressOverlay active={loading && loadingKind === 'next_quarter'} />
          {gamePhase !== 'HOME' && <TaskPanel />}
          {gamePhase === 'HOME' && (
            <ScenarioHomePanel
              selectedId={scenarioId}
              loading={scenarioHomeLoading}
              error={scenarioHomeError}
              onSelect={(id) => {
                clearError();
                clearMingError();
                setScenarioId(id);
                if (isSalvageScenario(id)) {
                  setActiveSalvageScenarioId(id);
                  setSalvageMenuOpen(true);
                } else {
                  setSalvageMenuOpen(false);
                }
              }}
              onBack={() => setHomeView('portal')}
              onClearError={clearScenarioHomeError}
              salvageMenuMode
              onEnterSalvageMenu={() => setSalvageMenuOpen(true)}
              canContinue={!!scenarioId && canContinueSalvageScenario(scenarioId)}
              onContinue={() => {
                clearError();
                clearMingError();
                if (scenarioId) setActiveSalvageScenarioId(scenarioId);
                void handleMingContinueGame();
              }}
              onStart={() => {
                clearError();
                clearMingError();
                if (scenarioId && isSalvageScenario(scenarioId)) {
                  setActiveSalvageScenarioId(scenarioId);
                  void handleMingStartGame();
                } else {
                  void handleStartGame();
                }
              }}
            />
          )}
          {gamePhase === 'HOME' &&
            salvageMenuOpen &&
            scenarioId &&
            isSalvageScenario(scenarioId) &&
            !mingActive && (
            <MingMenuHome scenarioId={scenarioId} onBack={() => setSalvageMenuOpen(false)} />
          )}
          {gamePhase === 'EVENT_RESOLUTION' && currentEvent && (
            <div
              style={{
                position: 'absolute',
                right: 72,
                top: 84,
                width: 360,
                borderRadius: 10,
                border: '1px solid rgba(255,215,0,0.35)',
                background: 'rgba(10, 8, 12, 0.95)',
                padding: 12,
                color: '#f5f5f5',
              }}
            >
              <div style={{ color: '#ffd700', marginBottom: 6, fontWeight: 700 }}>{currentEvent.title}</div>
              <div style={{ color: '#c8c0a8', fontSize: 12, marginBottom: 8 }}>{currentEvent.description || '请做出选择。'}</div>
              {currentEvent.choices.map((choice) => (
                <button
                  key={choice.id}
                  onClick={() => {
                    void handleSelectEventOption(choice.id);
                  }}
                  disabled={loading}
                  title={choice.effectsText.join(' | ')}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    marginBottom: 8,
                    borderRadius: 8,
                    border: '1px solid rgba(255,215,0,0.25)',
                    background: 'rgba(0,0,0,0.4)',
                    color: '#eee',
                    padding: 8,
                    cursor: 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {choice.text}
                </button>
              ))}
            </div>
          )}
          {gamePhase === 'FOCUS_SELECTION' && (
            <div
              style={{
                position: 'absolute',
                right: 72,
                top: 84,
                width: 360,
                borderRadius: 10,
                border: '1px solid rgba(255,215,0,0.35)',
                background: 'rgba(10, 8, 12, 0.95)',
                padding: 12,
                color: '#f5f5f5',
              }}
            >
              <div style={{ color: '#ffd700', marginBottom: 6, fontWeight: 700 }}>季度重心（四选三）</div>
              <div style={{ color: '#c8c0a8', fontSize: 12, marginBottom: 8 }}>请选择 3 项后提交。</div>
              {focusOptions.map((option) => {
                const active = selectedFocus.includes(option.key);
                return (
                  <button
                    key={option.key}
                    onClick={() => {
                      if (loading) return;
                      const has = selectedFocus.includes(option.key);
                      const next = has
                        ? selectedFocus.filter((x) => x !== option.key)
                        : [...selectedFocus, option.key];
                      setSelectedFocus(next.length <= 3 ? next : selectedFocus);
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      marginBottom: 8,
                      borderRadius: 8,
                      border: active ? '1px solid rgba(255,215,0,0.85)' : '1px solid rgba(255,215,0,0.25)',
                      background: active ? 'rgba(255,215,0,0.14)' : 'rgba(0,0,0,0.4)',
                      color: '#eee',
                      padding: 8,
                      cursor: 'pointer',
                    }}
                  >
                    {option.label}
                  </button>
                );
              })}
              <button
                disabled={loading || selectedFocus.length !== 3}
                onClick={() => {
                  void handleSelectQuarterFocus(selectedFocus);
                }}
                style={{
                  width: '100%',
                  border: 'none',
                  borderRadius: 8,
                  padding: '8px 10px',
                  color: '#1b1010',
                  fontWeight: 700,
                  background: 'linear-gradient(90deg, #ffd700, #c41e3a)',
                  opacity: loading || selectedFocus.length !== 3 ? 0.6 : 1,
                  cursor: 'pointer',
                }}
              >
                {loading ? '提交中…' : '提交季度重心'}
              </button>
            </div>
          )}
          {gamePhase === 'QUARTER_SETTLEMENT' && (
            <div
              style={{
                position: 'absolute',
                right: 72,
                top: 84,
                width: 420,
                maxHeight: '70vh',
                overflowY: 'auto',
                borderRadius: 10,
                border: '1px solid rgba(255,215,0,0.35)',
                background: 'rgba(10, 8, 12, 0.95)',
                padding: 12,
                color: '#f5f5f5',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: 8,
                  marginBottom: 8,
                }}
              >
                <span style={{ color: '#ffd700', fontWeight: 700 }}>第{currentQuarter}季度结算</span>
                <button
                  type="button"
                  onClick={openQuarterReport}
                  style={{
                    border: '1px solid rgba(255,215,0,0.45)',
                    borderRadius: 6,
                    background: 'rgba(255,215,0,0.12)',
                    color: '#ffebc1',
                    fontSize: 12,
                    padding: '4px 10px',
                    cursor: 'pointer',
                    whiteSpace: 'nowrap',
                  }}
                  title={
                    quarterReportDisplay.hasContent
                      ? quarterReportDisplay.title
                      : '完成「下季」推进后，将展示后端生成的朝政纪要'
                  }
                >
                  季度报告
                </button>
              </div>
              <div style={{ marginBottom: 6, fontSize: 12, lineHeight: 1.5 }}>
                {settlement?.taskStats
                  ? formatTaskSettlementLine(settlement.taskStats)
                  : '上季结算：—'}
              </div>
              <div style={{ marginBottom: 8, fontSize: 12, lineHeight: 1.5 }}>
                {settlement?.taskStats
                  ? formatCurrentPoolLine(settlement.taskStats)
                  : '本季任务池：—'}
              </div>
              <div style={{ marginBottom: 8, fontSize: 12 }}>
                事件影响：{(settlement?.eventSummary || []).join(' / ') || '无'}
              </div>
              <div style={{ marginBottom: 8, fontSize: 12, lineHeight: 1.5 }}>
                <div style={{ color: '#ffebc1', marginBottom: 4 }}>本季任务怠政与逾期</div>
                {(settlement?.taskQuarterEndLines || ['本季任务季末：—']).map((line, i) => (
                  <div key={`task-quarter-end-${i}`} style={{ color: '#d8d0c0', marginBottom: 2 }}>
                    {line}
                  </div>
                ))}
              </div>
              <div style={{ marginBottom: 8, fontSize: 12, lineHeight: 1.5 }}>
                <div style={{ color: '#ffebc1', marginBottom: 4 }}>诏书影响</div>
                {(settlement?.decreeImpactLines || ['无']).map((line, i) => (
                  <div key={`decree-impact-${i}`} style={{ color: '#d8d0c0', marginBottom: 2 }}>
                    {line}
                  </div>
                ))}
              </div>
              <div
                style={{
                  marginBottom: 8,
                  fontSize: 12,
                  lineHeight: 1.55,
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: '1px solid rgba(160,120,255,0.35)',
                  background: 'rgba(40,24,56,0.35)',
                }}
              >
                <div style={{ color: '#c9b0ff', fontWeight: 700, marginBottom: 6 }}>
                  人物对策（Agent A）
                </div>
                <div style={{ color: agentFlowDisplay.hasContent ? '#e8dff8' : '#a898b8', marginBottom: 4 }}>
                  {agentFlowDisplay.statusLine}
                </div>
                {agentFlowDisplay.explanationZh ? (
                  <div style={{ color: '#d8cce8', marginBottom: 4 }}>
                    {agentFlowDisplay.explanationZh}
                    {agentFlowDisplay.riskLevel ? `（风险：${agentFlowDisplay.riskLevel}）` : ''}
                  </div>
                ) : null}
                {agentFlowDisplay.contestLines.map((line, i) => (
                  <div key={`agent-contest-${i}`} style={{ color: '#dcc8f0', marginBottom: 2 }}>
                    朝议：{line}
                  </div>
                ))}
                {agentFlowDisplay.counterLines.map((line, i) => (
                  <div key={`agent-counter-${i}`} style={{ color: '#dcc8f0', marginBottom: 2 }}>
                    对策：{line}
                  </div>
                ))}
                {agentFlowDisplay.proposalLines.map((line, i) => (
                  <div key={`agent-proposal-${i}`} style={{ color: '#b8e8c8', marginBottom: 2 }}>
                    数值提案：{line}
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10, marginBottom: 6, color: '#ffd700', fontWeight: 700 }}>
                数值变化
              </div>
              <div style={{ display: 'grid', gap: 6 }}>
                {settlementMetricRows.map((row) => (
                  <div
                    key={row.key}
                    style={{
                      display: 'grid',
                      gridTemplateColumns: '70px 1fr 1fr 1fr',
                      gap: 8,
                      fontSize: 12,
                      borderTop: '1px solid rgba(255,215,0,0.12)',
                      paddingTop: 4,
                    }}
                  >
                    <span style={{ color: '#ffebc1' }}>{row.label}</span>
                    <span style={{ color: '#bfb8a0' }}>前 {row.before}</span>
                    <span style={{ color: '#bfb8a0' }}>后 {row.after}</span>
                    <span style={{ color: row.delta >= 0 ? '#7CFC98' : '#FF8080' }}>
                      {row.delta >= 0 ? `+${row.delta}` : row.delta}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {gamePhase === 'SKILL_ALLOCATION' && (
            <div
              style={{
                position: 'absolute',
                right: 72,
                top: 84,
                width: 460,
                maxHeight: '72vh',
                overflowY: 'auto',
                borderRadius: 10,
                border: '1px solid rgba(106,168,255,0.45)',
                background: 'rgba(10, 12, 20, 0.96)',
                padding: 12,
                color: '#f5f5f5',
              }}
            >
              <div style={{ color: '#8fc0ff', marginBottom: 8, fontWeight: 700 }}>
                技能加点（本季度开局）
              </div>
              <div style={{ marginBottom: 10, fontSize: 12, color: '#c8d8f5' }}>
                剩余点数：军 {remainingWallet.military} ｜ 管 {remainingWallet.management} ｜ 学 {remainingWallet.scholarship} ｜ 政 {remainingWallet.politics} ｜ 通 {remainingWallet.generic}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 6, marginBottom: 10 }}>
                {skillTabs.map((tab) => {
                  const active = skillUi.activeTree === tab.key;
                  const tabDisabled = Boolean(skillTabFocusSet && !skillTabFocusSet.has(tab.key));
                  return (
                    <button
                      key={tab.key}
                      type="button"
                      disabled={tabDisabled}
                      title={tabDisabled ? '本季未选该重心，无法在此树加点' : undefined}
                      onClick={() => {
                        if (tabDisabled) return;
                        handleSwitchSkillTree(tab.key);
                      }}
                      style={{
                        borderRadius: 8,
                        border: active
                          ? '1px solid rgba(143,192,255,0.95)'
                          : '1px solid rgba(143,192,255,0.35)',
                        background: active ? 'rgba(120,170,255,0.2)' : 'rgba(0,0,0,0.3)',
                        color: '#f0f4ff',
                        padding: '6px 8px',
                        cursor: tabDisabled ? 'not-allowed' : 'pointer',
                        opacity: tabDisabled ? 0.38 : 1,
                      }}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>
              <div style={{ display: 'grid', gap: 6, marginBottom: 10 }}>
                {activeSkillNodes.map((node) => {
                  const isFull = node.currentLevel >= node.maxLevel;
                  const canAfford =
                    Number(remainingWallet[skillUi.activeTree] || 0) + Number(remainingWallet.generic || 0) >= node.cost;
                  const canAdd = !isFull && canAfford;
                  return (
                    <button
                      key={node.id}
                      onClick={() => {
                        handleOpenSkillNodeDetail(node.id);
                      }}
                      style={{
                        textAlign: 'left',
                        borderRadius: 8,
                        border: '1px solid rgba(143,192,255,0.35)',
                        background: isFull
                          ? 'rgba(60,130,80,0.35)'
                          : canAdd
                            ? 'rgba(80,120,200,0.35)'
                            : 'rgba(90,90,90,0.28)',
                        color: '#f0f4ff',
                        padding: 8,
                        cursor: 'pointer',
                      }}
                    >
                      <div style={{ fontWeight: 700 }}>{node.name}</div>
                      <div style={{ fontSize: 12, color: '#d4def4' }}>
                        等级 {node.currentLevel}/{node.maxLevel} | 消耗 {node.cost}
                      </div>
                      <div style={{ fontSize: 12, color: '#b7c6e2' }}>{node.description}</div>
                    </button>
                  );
                })}
              </div>
              {openSkillNode && (
                <div
                  style={{
                    border: '1px solid rgba(143,192,255,0.45)',
                    borderRadius: 8,
                    padding: 8,
                    background: 'rgba(0,0,0,0.28)',
                    marginBottom: 10,
                  }}
                >
                  <div style={{ color: '#8fc0ff', fontWeight: 700, marginBottom: 4 }}>
                    {openSkillNode.name}
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>{openSkillNode.description}</div>
                  <div style={{ fontSize: 12, marginBottom: 4 }}>
                    当前等级：{openSkillNode.currentLevel}/{openSkillNode.maxLevel}
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 6 }}>
                    消耗：{skillUi.activeTree} 点 {openSkillNode.cost}
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 6 }}>
                    当前可用：{skillUi.activeTree} 点 {remainingWallet[skillUi.activeTree]}，通用点 {remainingWallet.generic}
                  </div>
                  <div style={{ fontSize: 12, marginBottom: 6 }}>
                    {openSkillNode.effects.map((e) => `- ${e}`).join('；')}
                  </div>
                  <button
                    disabled={
                      loading ||
                      openSkillNode.currentLevel >= openSkillNode.maxLevel ||
                      Number(remainingWallet[skillUi.activeTree] || 0) + Number(remainingWallet.generic || 0) < openSkillNode.cost
                    }
                    onClick={() => {
                      handleAllocateSkillPoint(openSkillNode.id);
                    }}
                    style={{
                      border: 'none',
                      borderRadius: 8,
                      padding: '7px 10px',
                      color: '#0d182d',
                      background: 'linear-gradient(90deg, #8fc0ff, #b4d7ff)',
                      cursor: 'pointer',
                      opacity:
                        loading ||
                        openSkillNode.currentLevel >= openSkillNode.maxLevel ||
                        Number(remainingWallet[skillUi.activeTree] || 0) + Number(remainingWallet.generic || 0) < openSkillNode.cost
                          ? 0.5
                          : 1,
                    }}
                  >
                    加点
                  </button>
                </div>
              )}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <button
                  onClick={handleCancelSkillAllocation}
                  style={{
                    borderRadius: 8,
                    border: '1px solid rgba(220,220,220,0.4)',
                    background: 'rgba(0,0,0,0.4)',
                    color: '#f2f2f2',
                    padding: '8px 10px',
                    cursor: 'pointer',
                  }}
                >
                  取消
                </button>
                <button
                  disabled={loading}
                  onClick={() => {
                    void handleConfirmSkillAllocation();
                  }}
                  style={{
                    border: 'none',
                    borderRadius: 8,
                    color: '#0d182d',
                    padding: '8px 10px',
                    fontWeight: 700,
                    background: 'linear-gradient(90deg, #8fc0ff, #5f9fff)',
                    cursor: 'pointer',
                    opacity: loading ? 0.6 : 1,
                  }}
                >
                  {skillSubmitEnabled ? '确认加点并进入朝政' : '返回（未提交加点）'}
                </button>
              </div>
            </div>
          )}
          {gamePhase === 'CAMPAIGN_MILESTONE' && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'grid',
                placeItems: 'center',
                background: 'rgba(0,0,0,0.55)',
                zIndex: 30,
              }}
            >
              <div
                style={{
                  maxWidth: 520,
                  padding: '20px 24px',
                  borderRadius: 12,
                  background: 'linear-gradient(180deg,#1a1208,#2a1a0a)',
                  border: '1px solid rgba(255,215,0,0.55)',
                  color: '#f5ecd7',
                }}
              >
                <div style={{ color: '#ffd700', fontWeight: 700, fontSize: 20, marginBottom: 10 }}>
                  {campaignEpilogue?.title_zh || '熙宁第一阶段可收束'}
                </div>
                <div style={{ lineHeight: 1.6, marginBottom: 16, fontSize: 14 }}>
                  {campaignMilestonePrompt || campaignEpilogue?.summary_zh}
                </div>
                <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => {
                      void handleCampaignMilestoneContinue();
                    }}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 8,
                      border: '1px solid rgba(255,215,0,0.45)',
                      background: 'rgba(40,30,20,0.9)',
                      color: '#ffebc8',
                      cursor: 'pointer',
                    }}
                  >
                    继续至季限
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      void handleCampaignMilestoneEnd();
                    }}
                    style={{
                      padding: '8px 14px',
                      borderRadius: 8,
                      border: 'none',
                      background: 'linear-gradient(90deg,#8fc0ff,#5f9fff)',
                      color: '#0d182d',
                      fontWeight: 700,
                      cursor: 'pointer',
                    }}
                  >
                    收束好结局
                  </button>
                </div>
              </div>
            </div>
          )}
          {gamePhase === 'GAME_END' && (
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'center',
                overflow: 'auto',
                padding: '32px 24px',
              }}
            >
              <div style={{ maxWidth: 960, width: '100%', paddingBottom: 48 }}>
                {typeof campaignEpilogue?.score === 'number' && (
                  <div style={{ color: '#ffd700', fontWeight: 700, fontSize: 22, marginBottom: 8 }}>
                    评分：{campaignEpilogue.score}
                    {campaignEpilogue.score_label_zh
                      ? ` · ${campaignEpilogue.score_label_zh}`
                      : ''}
                  </div>
                )}
                <div style={{ color: '#ffd700', fontWeight: 700, fontSize: 26, marginBottom: 16 }}>
                  {campaignEpilogue?.title_zh ||
                    (scenarioId === 'song_xining' ? '熙宁战役结束' : '五季已毕')}
                </div>
                {loading && (
                  <div style={{ color: '#c9b896', marginBottom: 12, fontSize: 14 }}>
                    国史编纂官正在撰写结局总评…
                  </div>
                )}
                <EndingReportTables
                  nationState={nationState}
                  openingMetrics={campaignOpeningMetrics}
                  quarterChapters={quarterChapters}
                  scenarioId={scenarioId}
                  currentQuarter={currentQuarter}
                  latestReport={latestQuarterReport}
                  highlightsZh={campaignEpilogue?.highlights_zh}
                />
                {[
                  ['生平事迹', campaignEpilogue?.sections?.life_chronicle_zh],
                  ['结局描述', campaignEpilogue?.sections?.ending_scene_zh],
                  ['功过总结', campaignEpilogue?.sections?.merits_demerits_zh],
                  ['庙号', campaignEpilogue?.sections?.temple_name_zh],
                  ['未来推演', campaignEpilogue?.sections?.future_projection_zh],
                ].map(([label, text]) =>
                  text ? (
                    <div key={label} style={{ marginBottom: 20 }}>
                      <div
                        style={{
                          color: '#e8c878',
                          fontWeight: 700,
                          fontSize: 16,
                          marginBottom: 8,
                        }}
                      >
                        {label}
                      </div>
                      <div
                        style={{
                          color: '#e8dcc0',
                          lineHeight: 1.75,
                          fontSize: 15,
                          whiteSpace: 'pre-wrap',
                        }}
                      >
                        {text}
                      </div>
                    </div>
                  ) : null,
                )}
                {!campaignEpilogue?.sections?.life_chronicle_zh && (
                  <div style={{ color: '#e8dcc0', lineHeight: 1.7, fontSize: 15, whiteSpace: 'pre-wrap' }}>
                    {campaignEpilogue?.summary_zh || '游戏结束'}
                  </div>
                )}
                {(campaignEpilogue?.history_compare_zh || '').length > 0 && (
                  <div style={{ marginTop: 16, color: '#b8a888', fontSize: 14, lineHeight: 1.7 }}>
                    {campaignEpilogue?.history_compare_zh}
                  </div>
                )}
              </div>
            </div>
          )}
          {error && (
            <div
              style={{
                position: 'absolute',
                left: '50%',
                transform: 'translateX(-50%)',
                top: 60,
                background: 'rgba(80,0,0,0.9)',
                border: '1px solid rgba(255,120,120,0.6)',
                color: '#ffd3d3',
                borderRadius: 8,
                padding: '8px 10px',
                fontSize: 12,
              }}
            >
              {error}
              <button
                onClick={clearError}
                style={{ marginLeft: 10, border: 'none', background: 'transparent', color: '#fff', cursor: 'pointer' }}
              >
                关闭
              </button>
            </div>
          )}
        </div>
      </div>
      <TimelineLog />
      <MemorialListDrawer />
      <AIDialogPanel />
      <QuarterReportModal
        open={ui.isQuarterReportOpen}
        report={latestQuarterReport}
        currentQuarter={currentQuarter}
        scenarioId={scenarioId}
        onClose={closeQuarterReport}
      />
      <QuarterChapterDetailModal
        open={ui.isQuarterChapterDetailOpen}
        detail={quarterChapterDetail}
        onClose={closeQuarterChapterDetail}
      />
      <EdictComposerPanel />
    </div>
  );
};

