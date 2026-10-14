'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { TopStatusBar } from '../TopStatusBar';
import { MingMapScenePanel } from './map/MingMapScenePanel';
import { EdgeDockRail } from '../EdgeDockRail';
import { useMingStore } from '../../game/ming/mingStore';
import { MING_BG } from '../../game/ming/mingUiStyles';
import { MingPhaseBarDock } from './MingPhaseBarDock';
import { MingLeftCommandRail } from './MingLeftCommandRail';
import { MingSummonPanel } from './MingSummonPanel';
import { MingDirectivePanel } from './MingDirectivePanel';
import { MingDecreePanel } from './MingDecreePanel';
import { MingDecisionModal } from './MingDecisionModal';
import { MingTimelineLog } from './MingTimelineLog';
import { MingIssuesPanel } from './MingIssuesPanel';
import { MingSituationDrawer } from './MingSituationDrawer';
import { MingClosedIssuesModal } from './MingClosedIssuesModal';
import { MingReportModal } from './MingReportModal';
import { MingExtractionModal } from './MingExtractionModal';
import { MingSecretOrdersModal } from './MingSecretOrdersModal';
import { MingHistoryModal } from './MingHistoryModal';
import { MingStateModal } from './MingStateModal';
import { MingEdictModal } from './MingEdictModal';
import { MingCourtChatModal } from './MingCourtChatModal';
import { MingSettlementLock } from './MingSettlementLock';
import { MingEndingModal } from './MingEndingModal';
import { MingRightHudNav } from './MingRightHudNav';
import { MingLongGoalsModal } from './MingLongGoalsModal';
import { MingGameMenuModal } from './MingGameMenuModal';
import { MingCheatConsole } from './MingCheatConsole';
import { MingCourtDrawer } from './drawers/MingCourtDrawer';
import { MingAppointmentDrawer } from './drawers/MingAppointmentDrawer';
import { MingRegionDrawer } from './drawers/MingRegionDrawer';
import { MingArmyDrawer } from './drawers/MingArmyDrawer';
import { MingEconomyDrawer } from './drawers/MingEconomyDrawer';
import { MingBuildingDrawer } from './drawers/MingBuildingDrawer';
import { MingHaremDrawer } from './drawers/MingHaremDrawer';
import type { MingHudDrawerKey, SalvageMinister } from '../../game/ming/salvageStateTypes';
import type { MingCommandModal, MingClosedIssue, MingTurnPhase } from '../../game/ming/mingTurnPhase';
import { mingPrimaryBtn } from '../../game/ming/mingUiStyles';
import type { ScenarioId } from '../../game/scenarios';
import { getScenario, resolveSalvageScenarioId, labelSalvageScenario } from '../../game/scenarios';
import { mingFetchSecretOrders, mingFetchConsortCandidates, mingSelectConsort, mingUploadMinisterPortrait } from '../../lib/mingApi';

type Props = {
  scenarioId: ScenarioId;
  onBackToScenarioSelect: () => void;
};

export const MingGameShell: React.FC<Props> = ({ scenarioId, onBackToScenarioSelect }) => {
  const {
    loading,
    error,
    clearError,
    state,
    salvageRaw,
    nationState,
    characters,
    decreeText,
    lastReport,
    settleStage,
    settleThinking,
    settleNarrative,
    postSettleReport,
    clearPostSettleReport,
    chatHistory,
    activeMinisterId,
    activeMinisterMeta,
    chatSuggestions,
    streamingMinisterReply,
    pendingUserMessage,
    chatNotice,
    chatBusy,
    ministerSecretOrders,
    setActiveMinister,
    sendMinisterChat,
    undoMinisterChat,
    createMinisterSecretOrder,
    uploadMinisterPortrait,
    toggleMinisterFavorite,
    archiveActiveMinister,
    confirmDirective,
    rejectDirective,
    deleteDirective,
    patchDirective,
    confirmAllDirectives,
    addManualDirective,
    addCourtChatDirective,
    saveStructuredDirective,
    deleteStructuredDirective,
    composeDecree,
    saveDecreeEdit,
    issueDecree,
    submitDecisions,
    cancelSettlement,
    pendingDecisions,
    restoreSession,
    handleExit,
    refreshState,
    cheatDirective,
    setCheatDirective,
    uiResetNonce,
    boundScenarioId,
    fetchMenuBootstrap,
    handleStartGame,
  } = useMingStore();

  const [showLeftRail, setShowLeftRail] = useState(false);
  const [showRightRail, setShowRightRail] = useState(false);
  const [summonOpen, setSummonOpen] = useState(false);
  const [directiveOpen, setDirectiveOpen] = useState(false);
  const [decreeOpen, setDecreeOpen] = useState(false);
  const [issuesOpen, setIssuesOpen] = useState(false);
  const [situationDrawerOpen, setSituationDrawerOpen] = useState(false);
  const [closedModal, setClosedModal] = useState<MingClosedIssue[]>([]);
  const [closedShown, setClosedShown] = useState(-1);
  const [activeModal, setActiveModal] = useState<MingCommandModal>('none');
  const [gazetteReport, setGazetteReport] = useState('');
  const [gazetteShown, setGazetteShown] = useState(-1);
  const [endingDismissed, setEndingDismissed] = useState(false);
  const [secretOrderBadge, setSecretOrderBadge] = useState(0);
  const [hudDrawer, setHudDrawer] = useState<MingHudDrawerKey>('none');
  const [longGoalsOpen, setLongGoalsOpen] = useState(false);
  const [cheatOpen, setCheatOpen] = useState(false);
  const [consortCandidates, setConsortCandidates] = useState<SalvageMinister[]>([]);

  const resetLocalUi = () => {
    setSummonOpen(false);
    setDirectiveOpen(false);
    setDecreeOpen(false);
    setIssuesOpen(false);
    setSituationDrawerOpen(false);
    setHudDrawer('none');
    setLongGoalsOpen(false);
    setActiveModal('none');
    setClosedModal([]);
    setCheatOpen(false);
    setConsortCandidates([]);
  };

  useEffect(() => {
    if (uiResetNonce > 0) resetLocalUi();
  }, [uiResetNonce]);

  useEffect(() => {
    if (hudDrawer !== 'harem') return;
    void mingFetchConsortCandidates()
      .then((out) => setConsortCandidates(out.candidates || []))
      .catch(() => setConsortCandidates([]));
  }, [hudDrawer]);

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if (event.ctrlKey && (event.key === '~' || event.key === '`')) {
        event.preventDefault();
        setCheatOpen((v) => !v);
        return;
      }
      if (event.key !== 'Escape') return;
      if (loading && (settleStage || settleThinking || settleNarrative)) return;
      event.preventDefault();
      if (cheatOpen) {
        setCheatOpen(false);
        return;
      }
      if (activeModal === 'menu') {
        setActiveModal('none');
        return;
      }
      if (activeModal !== 'none') {
        if (activeModal === 'court_chat') setActiveModal('edict');
        else setActiveModal('none');
        return;
      }
      if (longGoalsOpen) {
        setLongGoalsOpen(false);
        return;
      }
      if (summonOpen) {
        setSummonOpen(false);
        return;
      }
      if (closedModal.length) {
        setClosedModal([]);
        return;
      }
      if (hudDrawer !== 'none') {
        setHudDrawer('none');
        return;
      }
      if (situationDrawerOpen) {
        setSituationDrawerOpen(false);
        return;
      }
      if (issuesOpen) {
        setIssuesOpen(false);
        return;
      }
      if (directiveOpen || decreeOpen) {
        setDirectiveOpen(false);
        setDecreeOpen(false);
        return;
      }
      setActiveModal('menu');
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [
    loading,
    settleStage,
    settleThinking,
    settleNarrative,
    cheatOpen,
    activeModal,
    longGoalsOpen,
    summonOpen,
    closedModal.length,
    hudDrawer,
    situationDrawerOpen,
    issuesOpen,
    directiveOpen,
    decreeOpen,
  ]);

  useEffect(() => {
    void restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    void fetchMenuBootstrap();
  }, [fetchMenuBootstrap]);

  const expectedSalvageId = resolveSalvageScenarioId(scenarioId);
  const activeSalvageMismatch = Boolean(
    boundScenarioId && boundScenarioId !== expectedSalvageId,
  );

  const phase = (state?.turn_phase || 'summoning') as MingTurnPhase;
  const consultable = useMemo(
    () => characters.filter((c) => c.consultable !== false && c.id !== 'emperor'),
    [characters],
  );

  const edictBadge =
    (state?.directives?.length || 0) + (state?.structured_directives?.length || 0);

  useEffect(() => {
    if (!state) return;
    const closed = state.closed_this_turn || [];
    const currentTurn = state.turn.turn;
    if (closed.length && currentTurn !== closedShown) {
      setClosedModal(closed);
      setClosedShown(currentTurn);
    }
  }, [state, closedShown]);

  useEffect(() => {
    if (!state) return;
    if (!state.ending) return;
    if (endingDismissed) return;
    setActiveModal('ending');
  }, [state, endingDismissed]);

  useEffect(() => {
    if (!state) return;
    const currentTurn = state.turn.turn;
    void mingFetchSecretOrders()
      .then(({ orders }) => {
        const n = (orders || []).filter(
          (o) => o.status === 'active' || o.status === 'pending_review',
        ).length;
        setSecretOrderBadge(n);
      })
      .catch(() => undefined);
    if (state.ended) return;
    if (state.ending && !endingDismissed) return;
    const summary = (state.previous_summary || '').trim();
    if (!summary || summary.startsWith('登基伊始')) return;
    if (currentTurn === gazetteShown) return;
    setGazetteReport(summary);
    setActiveModal('report');
    setGazetteShown(currentTurn);
  }, [state, gazetteShown, endingDismissed]);

  useEffect(() => {
    if (!postSettleReport) return;
    if (state?.ending && !endingDismissed) return;
    setGazetteReport('');
    setActiveModal('report');
    clearPostSettleReport();
  }, [postSettleReport, state?.ending, endingDismissed, clearPostSettleReport]);

  const openEdict = () => {
    setActiveModal('edict');
    setDirectiveOpen(true);
    setDecreeOpen(true);
    setSummonOpen(false);
  };

  const handlePhaseClick = (target: MingTurnPhase) => {
    switch (target) {
      case 'summoning':
        setActiveModal('none');
        setHudDrawer('none');
        setSummonOpen(true);
        setDirectiveOpen(false);
        setDecreeOpen(false);
        break;
      case 'reviewing':
      case 'awaiting_decision':
      case 'issued':
        openEdict();
        break;
      default:
        break;
    }
  };

  const settling = loading && Boolean(settleStage || settleThinking || settleNarrative);
  const decreeBottom = directiveOpen && decreeOpen ? 360 : 102;

  const pendingForChat = useMemo(() => {
    const name = characters.find((c) => c.id === activeMinisterId)?.name;
    if (!name) return [];
    return (state?.directives || []).filter((d) => d.status === 'pending' && d.actor === name);
  }, [state?.directives, activeMinisterId, characters]);

  const openSummonForMinister = (name: string) => {
    const char = characters.find((c) => c.name === name || c.id === name);
    if (char) {
      setActiveMinister(char.id);
      setSummonOpen(true);
    }
    setActiveModal('none');
  };

  const toggleHudDrawer = (key: Exclude<MingHudDrawerKey, 'none'>) => {
    if (key === 'goal') {
      setLongGoalsOpen(true);
      setHudDrawer('none');
      return;
    }
    if (key === 'court') {
      setSummonOpen(false);
      setHudDrawer((prev) => (prev === 'court' ? 'none' : 'court'));
      return;
    }
    setHudDrawer((prev) => (prev === key ? 'none' : key));
  };

  const raw = salvageRaw;

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        background: MING_BG,
      }}
    >
      <TopStatusBar
        nationOverride={nationState}
        mingSalvageMetrics
        onBack={() => {
          handleExit();
          onBackToScenarioSelect();
        }}
        backLabel="← 返回选剧本"
        backDisabled={loading}
        onOpenGameMenu={() => setActiveModal('menu')}
        onYearClick={() => setActiveModal('state')}
        mingBudget={raw?.budget}
        mingLegacies={raw?.legacies}
        mingRegionWarning={raw?.region_warning}
        salvageScenarioId={scenarioId}
      />
      <MingPhaseBarDock phase={phase} onPhaseClick={handlePhaseClick} />

      {error && (
        <div
          style={{
            padding: '8px 16px',
            background: 'rgba(120,20,20,0.85)',
            color: '#fcc',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            fontSize: 13,
            zIndex: 200,
          }}
        >
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            style={{
              color: '#fff',
              cursor: 'pointer',
              background: 'transparent',
              border: 'none',
              fontSize: 13,
            }}
          >
            关闭
          </button>
        </div>
      )}

      {activeSalvageMismatch && (
        <div
          style={{
            padding: '10px 16px',
            background: 'rgba(120,80,10,0.92)',
            color: '#ffe7a3',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 12,
            fontSize: 13,
            zIndex: 200,
            flexWrap: 'wrap',
          }}
        >
          <span>
            当前进度属于「
            {getScenario(boundScenarioId as ScenarioId)?.labelZh ||
              labelSalvageScenario(boundScenarioId || '')}
            」，与所选「{getScenario(scenarioId)?.labelZh || scenarioId}」不一致。朝堂/兵部/工部数据会错乱，请返回选剧本并
            <strong>开始新游戏</strong>。
          </span>
          <button
            type="button"
            onClick={() => void handleStartGame()}
            style={{ ...mingPrimaryBtn, fontSize: 12, padding: '6px 12px', whiteSpace: 'nowrap' }}
          >
            立即新游戏
          </button>
        </div>
      )}

      <div style={{ flex: 1, position: 'relative', display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
          <EdgeDockRail
            side="left"
            open={showLeftRail}
            onOpen={() => setShowLeftRail(true)}
            onClose={() => setShowLeftRail(false)}
            railWidth={112}
          >
            <MingLeftCommandRail
              eventsCount={state?.issues?.length || 0}
              secretOrderBadge={secretOrderBadge}
              edictBadge={edictBadge}
              activeModal={activeModal}
              issuesOpen={issuesOpen}
              onOpenIssues={() => {
                setIssuesOpen((v) => !v);
                if (issuesOpen) setSituationDrawerOpen(false);
              }}
              onOpenEdict={openEdict}
              onOpen={(modal) => setActiveModal(modal)}
            />
          </EdgeDockRail>

          <EdgeDockRail
            side="right"
            open={showRightRail}
            onOpen={() => setShowRightRail(true)}
            onClose={() => setShowRightRail(false)}
            railWidth={52}
          >
            <MingRightHudNav
              embedded
              active={hudDrawer}
              onToggle={toggleHudDrawer}
              showLongGoals={scenarioId === 'ming_wanli'}
              isSong={scenarioId === 'song_xining_v2'}
            />
          </EdgeDockRail>

          <div style={{ position: 'absolute', inset: 0, zIndex: 0 }}>
            <MingMapScenePanel
              scenarioId={scenarioId}
              mapNodes={salvageRaw?.map_nodes}
              salvageRegions={salvageRaw?.regions}
              issues={state?.issues || []}
              onOpenSituation={() => setSituationDrawerOpen(true)}
            />
          </div>

          <MingSummonPanel
            open={summonOpen}
            phase={phase}
            characters={consultable}
            activeMinisterId={activeMinisterId}
            activeMinisterMeta={activeMinisterMeta}
            chatHistory={chatHistory}
            chatSuggestions={chatSuggestions}
            streamingReply={streamingMinisterReply}
            pendingUserMessage={pendingUserMessage}
            chatNotice={chatNotice}
            chatBusy={chatBusy}
            ministerSecretOrders={ministerSecretOrders}
            pendingDirectives={pendingForChat}
            ministers={raw?.ministers || []}
            onClose={() => setSummonOpen(false)}
            onSelectMinister={setActiveMinister}
            onClearMinister={() => setActiveMinister(null)}
            onSendChat={(msg) => void sendMinisterChat(msg)}
            onUndoChat={() => void undoMinisterChat()}
            onConfirmDirective={(id) => void confirmDirective(id)}
            onRejectDirective={(id) => void rejectDirective(id)}
            onToggleFavorite={() => void toggleMinisterFavorite()}
            onArchiveMinister={() => void archiveActiveMinister()}
            onUploadPortrait={(f) => void uploadMinisterPortrait(f)}
            onCreateSecretOrder={(t, c) => void createMinisterSecretOrder(t, c)}
            onOpenEdict={openEdict}
          />

          <MingIssuesPanel
            open={issuesOpen}
            issues={state?.issues || []}
            onClose={() => setIssuesOpen(false)}
            onOpenDrawer={() => {
              setIssuesOpen(false);
              setSituationDrawerOpen(true);
            }}
          />

          <MingSituationDrawer
            open={situationDrawerOpen}
            issues={state?.issues || []}
            closedIssues={state?.closed_this_turn || []}
            maxDecreeIssues={state?.max_decree_issues}
            characters={characters}
            salvageRaw={salvageRaw}
            scenarioId={scenarioId}
            onClose={() => setSituationDrawerOpen(false)}
            onChanged={() => void refreshState()}
          />

          <MingDirectivePanel
            open={directiveOpen && activeModal !== 'edict'}
            directives={state?.directives || []}
            pendingCount={state?.pending_count || 0}
            phase={phase}
            loading={loading}
            onClose={() => setDirectiveOpen(false)}
            onConfirm={(id) => void confirmDirective(id)}
            onReject={(id) => void rejectDirective(id)}
            onAddDraft={(t) => void addManualDirective(t)}
            onComposeDecree={() => void composeDecree()}
          />

          <MingDecreePanel
            open={decreeOpen && activeModal !== 'edict'}
            bottom={decreeBottom}
            decreeText={decreeText}
            lastReport={lastReport}
            settleStage={settleStage}
            settleNarrative={settleNarrative}
            loading={loading}
            phase={phase}
            onClose={() => setDecreeOpen(false)}
            onDecreeChange={(t) => useMingStore.setState({ decreeText: t })}
            onSaveDecree={() => void saveDecreeEdit(decreeText)}
            onIssue={() => void issueDecree()}
            onOpenSummon={() => setSummonOpen(true)}
          />

          <MingSettlementLock
            active={settling}
            stage={settleStage}
            thinking={settleThinking}
            narrative={settleNarrative}
            onCancel={cancelSettlement}
          />
        </div>

        <MingTimelineLog
          turnLabel={state?.turn.label}
          lastReport={lastReport}
          settleNarrative={settleNarrative}
          onOpenEdict={openEdict}
        />
      </div>

      {activeModal === 'report' && (
        <MingReportModal
          report={gazetteReport || lastReport || state?.previous_summary || ''}
          title={gazetteReport ? '邸报' : '月末奏疏'}
          subtitle={gazetteReport ? '上回合奏报' : '推演结果'}
          onClose={() => setActiveModal('none')}
        />
      )}

      {activeModal === 'extraction' && (
        <MingExtractionModal onClose={() => setActiveModal('none')} />
      )}

      {activeModal === 'secret_orders' && (
        <MingSecretOrdersModal
          onClose={() => setActiveModal('none')}
          onOpenMinister={openSummonForMinister}
        />
      )}

      {activeModal === 'history' && (
        <MingHistoryModal onClose={() => setActiveModal('none')} />
      )}

      {activeModal === 'state' && state && (
        <MingStateModal
          state={state}
          salvageRaw={salvageRaw}
          lastReport={lastReport}
          onClose={() => setActiveModal('none')}
        />
      )}

      {activeModal === 'ending' && state?.ending && (
        <MingEndingModal
          ending={state.ending}
          scenarioId={scenarioId}
          onClose={() => {
            setEndingDismissed(true);
            setActiveModal('none');
          }}
          onBackToMenu={() => {
            handleExit();
            onBackToScenarioSelect();
          }}
        />
      )}

      {activeModal === 'edict' && state && (
        <MingEdictModal
          state={state}
          phase={phase}
          decreeText={decreeText}
          lastReport={lastReport}
          settleStage={settleStage}
          settleNarrative={settleNarrative}
          loading={loading}
          salvageRaw={salvageRaw}
          scenarioId={scenarioId}
          onClose={() => setActiveModal('none')}
          onDecreeChange={(t) => useMingStore.setState({ decreeText: t })}
          onConfirm={(id) => void confirmDirective(id)}
          onReject={(id) => void rejectDirective(id)}
          onConfirmAll={() => void confirmAllDirectives()}
          onDelete={(id) => void deleteDirective(id)}
          onPatch={(id, text) => void patchDirective(id, text)}
          onAddDraft={(t) => void addManualDirective(t)}
          onDeleteStructured={(id) => void deleteStructuredDirective(id)}
          onSaveStructured={saveStructuredDirective}
          onComposeDecree={() => void composeDecree()}
          onSaveDecree={() => void saveDecreeEdit(decreeText)}
          onRewriteDecree={() => void composeDecree(true)}
          onIssue={() => void issueDecree()}
          onGoToCourtChat={() => {
            setActiveModal('court_chat');
          }}
        />
      )}

      {activeModal === 'court_chat' && (
        <MingCourtChatModal
          characters={characters}
          onClose={() => setActiveModal('edict')}
          onAfterChat={() => void refreshState()}
          onChooseDecision={async (option) => {
            await addCourtChatDirective(option);
            openEdict();
          }}
        />
      )}

      {activeModal === 'menu' && (
        <MingGameMenuModal
          onClose={() => setActiveModal('none')}
          onAfterLoad={() => {
            setActiveModal('none');
          }}
          onExitToMenu={async () => {
            handleExit();
            onBackToScenarioSelect();
          }}
        />
      )}

      {cheatOpen && (
        <MingCheatConsole
          directive={cheatDirective}
          onCommit={setCheatDirective}
          onClose={() => setCheatOpen(false)}
        />
      )}

      {closedModal.length > 0 && (
        <MingClosedIssuesModal
          items={closedModal}
          onClose={() => setClosedModal([])}
        />
      )}

      {pendingDecisions.length > 0 && !settling && (
        <MingDecisionModal
          decisions={pendingDecisions}
          onResolve={(choices) => void submitDecisions(choices)}
        />
      )}

      {state?.ended && !state?.ending && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.75)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 2000,
          }}
        >
          <div
            style={{
              padding: 24,
              borderRadius: 12,
              border: '1px solid rgba(255,215,0,0.6)',
              background: 'linear-gradient(180deg, #1b1010 0, #0d0b10 100%)',
              color: '#ffe7a3',
              textAlign: 'center',
              maxWidth: 420,
            }}
          >
            <h2 style={{ margin: '0 0 8px', fontSize: 20 }}>战役收束</h2>
            <p style={{ color: '#aaa', fontSize: 13, lineHeight: 1.6 }}>
              本局已结束，可返回选剧本重新开始。
            </p>
            <button
              type="button"
              onClick={onBackToScenarioSelect}
              style={{ ...mingPrimaryBtn, marginTop: 16 }}
            >
              返回选剧本
            </button>
          </div>
        </div>
      )}

      <MingCourtDrawer
        open={hudDrawer === 'court'}
        ministers={raw?.ministers || []}
        archivedMinisters={raw?.archived_ministers}
        scenarioId={scenarioId}
        onOpenChat={openSummonForMinister}
        onOpenCourtChat={() => setActiveModal('court_chat')}
        onChanged={() => void refreshState()}
        onClose={() => setHudDrawer('none')}
      />
      <MingAppointmentDrawer
        open={hudDrawer === 'appointment'}
        ministers={raw?.ministers || []}
        departments={raw?.departments}
        scenarioId={scenarioId}
        onOpenChat={openSummonForMinister}
        onClose={() => setHudDrawer('none')}
      />
      <MingRegionDrawer
        open={hudDrawer === 'region'}
        regions={raw?.regions || []}
        regionWarning={raw?.region_warning}
        scenarioId={scenarioId}
        onClose={() => setHudDrawer('none')}
      />
      <MingArmyDrawer
        open={hudDrawer === 'army'}
        armies={raw?.armies || []}
        armsStock={raw?.arms_stock}
        troopRates={raw?.troop_rates}
        scenarioId={scenarioId}
        onClose={() => setHudDrawer('none')}
      />
      <MingEconomyDrawer
        open={hudDrawer === 'economy'}
        budget={raw?.budget}
        treasuryText={raw?.treasury}
        onClose={() => setHudDrawer('none')}
      />
      <MingBuildingDrawer
        open={hudDrawer === 'building'}
        mapNodes={raw?.map_nodes}
        technologies={raw?.technologies}
        scenarioId={scenarioId}
        onClose={() => setHudDrawer('none')}
      />
      <MingHaremDrawer
        open={hudDrawer === 'harem'}
        consorts={raw?.consorts || []}
        candidates={consortCandidates}
        onOpenChat={openSummonForMinister}
        onUploadPortrait={async (name, file) => {
          await mingUploadMinisterPortrait(name, file);
          await refreshState();
        }}
        onSelectCandidate={async (name) => {
          await mingSelectConsort(name);
          await refreshState();
          const out = await mingFetchConsortCandidates();
          setConsortCandidates(out.candidates || []);
        }}
        onClose={() => setHudDrawer('none')}
      />
      {longGoalsOpen && scenarioId === 'ming_wanli' && (
        <MingLongGoalsModal onClose={() => setLongGoalsOpen(false)} />
      )}
    </div>
  );
};
