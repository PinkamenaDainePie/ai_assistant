'use client';

import React, { useMemo, useState } from 'react';
import { ATLAS_TIMELINE, DIALOGUE_QUICK_PROMPTS, TUTOR_QUICK_PROMPTS } from '../../game/portalContent';
import { buildSongMinisterCharacters } from '../../game/scenarios/songMinisterRoster';
import { CharacterPortrait } from '../CharacterPortrait';
import { CharacterNameTooltip } from '../CharacterNameTooltip';
import { postChat, postTutorChat } from '../../lib/renwuApi';
import { GlobeAtlasPanel } from './globe/GlobeAtlasPanel';
import { AtlasSlideIn } from './globe/AtlasSlideIn';
import { PortalModuleOverlay } from './PortalModuleOverlay';
import { PortalNav } from './PortalNav';
import {
  PortalBookIcon,
  PortalCompareIcon,
  PortalScrollIcon,
  PortalTimelineIcon,
} from './PortalCardIcons';
import { PortalThemeProvider, usePortalTheme } from './PortalThemeContext';

type ActiveModule = 'atlas' | 'dialogue' | 'tutor' | 'game' | null;

type PortalChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  citations?: Array<{ title?: string; era?: string }>;
};

let _portalMsgSeq = 0;
function nextPortalMsgId(prefix: string): string {
  _portalMsgSeq += 1;
  return `${prefix}-${_portalMsgSeq}`;
}

type CoursePortalHomeProps = {
  onEnterGame: () => void;
};

export const CoursePortalHome: React.FC<CoursePortalHomeProps> = (props) => (
  <PortalThemeProvider>
    <CoursePortalHomeInner {...props} />
  </PortalThemeProvider>
);

const CoursePortalHomeInner: React.FC<CoursePortalHomeProps> = ({ onEnterGame }) => {
  const [activeModule, setActiveModule] = useState<ActiveModule>(null);
  const ministers = useMemo(() => buildSongMinisterCharacters(), []);

  const [dialogueCharId, setDialogueCharId] = useState<string | null>(null);
  const [dialogueInput, setDialogueInput] = useState('');
  const [dialogueMessages, setDialogueMessages] = useState<PortalChatMessage[]>([]);
  const [dialogueLoading, setDialogueLoading] = useState(false);

  const [tutorInput, setTutorInput] = useState('');
  const [tutorMessages, setTutorMessages] = useState<PortalChatMessage[]>([]);
  const [tutorLoading, setTutorLoading] = useState(false);
  const { theme, toggling } = usePortalTheme();

  const dialogueChar = ministers.find((c) => c.id === dialogueCharId) ?? null;

  const openModule = (m: ActiveModule) => {
    if (m === 'game') {
      onEnterGame();
      return;
    }
    setActiveModule(m);
  };

  const sendDialogue = async (text: string) => {
    const msg = text.trim();
    if (!msg || !dialogueChar?.apiCharacterId || dialogueLoading) return;
    setDialogueMessages((prev) => [...prev, { id: nextPortalMsgId('dlg-u'), role: 'user', text: msg }]);
    setDialogueInput('');
    setDialogueLoading(true);
    try {
      const res = await postChat({
        character_id: dialogueChar.apiCharacterId,
        message: msg,
      });
      setDialogueMessages((prev) => [
        ...prev,
        { id: nextPortalMsgId('dlg-a'), role: 'assistant', text: res.reply || '（暂无回复）' },
      ]);
    } catch {
      setDialogueMessages((prev) => [
        ...prev,
        {
          id: nextPortalMsgId('dlg-a'),
          role: 'assistant',
          text: '暂时无法连接史家对话服务，请确认后端已启动。',
        },
      ]);
    } finally {
      setDialogueLoading(false);
    }
  };

  const sendTutor = async (text: string) => {
    const msg = text.trim();
    if (!msg || tutorLoading) return;
    setTutorMessages((prev) => [...prev, { id: nextPortalMsgId('tut-u'), role: 'user', text: msg }]);
    setTutorInput('');
    setTutorLoading(true);
    try {
      const history = tutorMessages.slice(-8).map((m) => ({
        role: m.role,
        content: m.text,
      }));
      const res = await postTutorChat({ message: msg, history, top_k: 8 });
      setTutorMessages((prev) => [
        ...prev,
        {
          id: nextPortalMsgId('tut-a'),
          role: 'assistant',
          text: res.reply || '（暂无回复）',
          citations: res.citations?.slice(0, 4),
        },
      ]);
    } catch {
      setTutorMessages((prev) => [
        ...prev,
        {
          id: nextPortalMsgId('tut-a'),
          role: 'assistant',
          text: '助教服务暂不可用。请确认后端已启动；若使用 Neo4j，请检查连接与图谱初始化（python -m tutor_module.seed）。',
        },
      ]);
    } finally {
      setTutorLoading(false);
    }
  };

  return (
    <div
      className={`portal-page${toggling ? ' portal-page--theme-transition' : ''}`}
      data-portal-theme={theme}
    >
      <PortalNav onNavigate={openModule} />

      <main className="portal-main">
        <section className="portal-hero">
          <div className="portal-hero__content">
            <div className="portal-hero__tags">
              <button type="button" className="portal-pill portal-pill--purple" onClick={() => openModule('atlas')}>
                制度演变
              </button>
              <button type="button" className="portal-pill portal-pill--blue" onClick={() => openModule('atlas')}>
                中西比较
              </button>
              <button type="button" className="portal-pill portal-pill--gold" onClick={() => openModule('game')}>
                制度模拟
              </button>
            </div>
            <h1 className="portal-hero__title">以制度之眼，读懂千年财税</h1>
            <p className="portal-hero__desc">
              图谱研习、史家对话、智能助学与制度模拟，
              <br className="portal-hero__desc-break" />
              帮助你在约束与博弈中理解中国财税制度的演变逻辑。
            </p>
            <div className="portal-hero__actions">
              <button type="button" className="portal-btn portal-btn--dark" onClick={() => openModule('atlas')}>
                探索财税史图谱
              </button>
              <button type="button" className="portal-btn portal-btn--ghost" onClick={() => openModule('game')}>
                进入制度模拟
              </button>
            </div>
          </div>
        </section>

        <section className="portal-section">
          <div className="portal-section__label">
            <span className="portal-pill portal-pill--purple">研习</span>
            <h2 className="portal-section__title">中西财税史图谱</h2>
          </div>
          <div className="portal-bento portal-bento--atlas">
            <button
              type="button"
              className="portal-card portal-card--purple portal-card--wide"
              onClick={() => openModule('atlas')}
            >
              <div className="portal-card__illus portal-card__illus--timeline" aria-hidden>
                <PortalTimelineIcon className="portal-card__icon" />
              </div>
              <div className="portal-card__tag">Timeline</div>
              <div className="portal-card__heading" role="heading" aria-level={3}>
                纵览历代改革节点
              </div>
              <div className="portal-card__text">
                从井田贡赋到熙宁新法，点击节点阅读制度摘要，理解路径依赖与时代约束。
              </div>
              <div className="portal-card__timeline-preview" aria-hidden>
                {ATLAS_TIMELINE.map((n) => (
                  <span key={n.id} className={`portal-card__dot portal-card__dot--${n.tone}`} title={n.title} />
                ))}
              </div>
              <span className="portal-card__cta">打开图谱 →</span>
            </button>
            <button
              type="button"
              className="portal-card portal-card--blue portal-card--tall"
              onClick={() => openModule('atlas')}
            >
              <div className="portal-card__illus portal-card__illus--compare" aria-hidden>
                <PortalCompareIcon className="portal-card__icon" />
              </div>
              <div className="portal-card__tag">Compare</div>
              <div className="portal-card__heading" role="heading" aria-level={3}>
                中西财政对照
              </div>
              <div className="portal-card__text">
                宋代商业财政 vs 罗马帝国汲取方式，并列理解国家能力来源。
              </div>
              <span className="portal-card__cta">查看对照 →</span>
            </button>
          </div>
        </section>

        <section className="portal-section">
          <div className="portal-section__label">
            <span className="portal-pill portal-pill--pink">互动</span>
            <h2 className="portal-section__title">AI 学习伴侣</h2>
          </div>
          <div className="portal-bento portal-bento--duo">
            <button
              type="button"
              className="portal-card portal-card--blue"
              onClick={() => openModule('dialogue')}
            >
              <div className="portal-card__illus portal-card__illus--scroll" aria-hidden>
                <PortalScrollIcon className="portal-card__icon" />
              </div>
              <div className="portal-card__tag">Dialogue</div>
              <div className="portal-card__heading" role="heading" aria-level={3}>
                AI 历史人物对话
              </div>
              <div className="portal-card__text">向王安石、司马光等提问，在论辩中体会改革者的权衡。</div>
              <span className="portal-card__cta">选人物开聊 →</span>
            </button>
            <button
              type="button"
              className="portal-card portal-card--pink"
              onClick={() => openModule('tutor')}
            >
              <div className="portal-card__illus portal-card__illus--book" aria-hidden>
                <PortalBookIcon className="portal-card__icon" />
              </div>
              <div className="portal-card__tag">Tutor</div>
              <div className="portal-card__heading" role="heading" aria-level={3}>
                AI 助教
              </div>
              <div className="portal-card__text">
                梳理知识点、推荐学习路径，随堂解答制度概念与比较问题。
              </div>
              <span className="portal-card__cta">向助教提问 →</span>
            </button>
          </div>
        </section>

        <section className="portal-section">
          <div className="portal-section__label">
            <span className="portal-pill portal-pill--gold">制度模拟</span>
            <h2 className="portal-section__title">财政改革情景决策</h2>
          </div>
          <button type="button" className="portal-card portal-card--gold portal-card--game" onClick={() => openModule('game')}>
            <div className="portal-card__game-preview" aria-hidden>
              <img
                src="/ui/portal/simulation-hero.png"
                alt=""
                className="portal-card__game-map"
              />
            </div>
            <div className="portal-card__game-copy">
              <div className="portal-card__tag">Simulation</div>
              <div className="portal-card__heading" role="heading" aria-level={3}>
                熙宁变法 · 制度模拟
              </div>
              <div className="portal-card__text">
                扮演神宗，下诏施政、听取奏对、推进季度结算。在九域地图与数值反馈中体验财政改革的真实约束——接入完整游戏流程。
              </div>
              <span className="portal-btn portal-btn--dark portal-card__game-btn">进入游戏 →</span>
            </div>
          </button>
        </section>

        <footer className="portal-footer">
          <span>财政税务学院 · 中国财税史智慧课程</span>
          <span>参考情景模拟引擎 · 宋代数据 biaoge/song</span>
        </footer>
      </main>

      <PortalModuleOverlay
        open={activeModule === 'atlas'}
        title="中西财税史图谱"
        subtitle="3D 地球 · 制度时间轴 · 中西对照"
        tone="purple"
        onClose={() => setActiveModule(null)}
      >
        <GlobeAtlasPanel
          onEnterGame={() => {
            setActiveModule(null);
            openModule('game');
          }}
        />
      </PortalModuleOverlay>

      <PortalModuleOverlay
        open={activeModule === 'dialogue'}
        title="AI 历史人物对话"
        subtitle="择一臣僚，就理财与变法发问"
        tone="blue"
        onClose={() => setActiveModule(null)}
      >
        <div className="portal-dialogue">
          <div className="portal-dialogue__pick">
            {ministers.slice(0, 8).map((c) => (
              <CharacterNameTooltip key={c.id} name={c.name} brief={c.brief} title={c.title}>
              <button
                type="button"
                className={`portal-dialogue__pick-btn${dialogueCharId === c.id ? ' portal-dialogue__pick-btn--active' : ''}`}
                onClick={() => {
                  setDialogueCharId(c.id);
                  setDialogueMessages([]);
                }}
              >
                <CharacterPortrait character={c} variant="portal" />
                <span>{c.name}</span>
              </button>
              </CharacterNameTooltip>
            ))}
          </div>
          {dialogueChar ? (
            <AtlasSlideIn animKey={dialogueChar.id} className="portal-dialogue__body">
              <div className="portal-chat__prompts">
                {DIALOGUE_QUICK_PROMPTS.map((p) => (
                  <button key={p} type="button" className="portal-pill portal-pill--blue" onClick={() => void sendDialogue(p)}>
                    {p}
                  </button>
                ))}
              </div>
              <div className="portal-chat__log">
                {dialogueMessages.length === 0 ? (
                  <AtlasSlideIn animKey={`empty-${dialogueChar.id}`}>
                    <p className="portal-chat__empty">向{dialogueChar.name}提出你的问题。</p>
                  </AtlasSlideIn>
                ) : (
                  dialogueMessages.map((m) => (
                    <AtlasSlideIn key={m.id} animKey={m.id}>
                      <div className={`portal-chat__msg portal-chat__msg--${m.role}`}>{m.text}</div>
                    </AtlasSlideIn>
                  ))
                )}
              </div>
              <form
                className="portal-chat__form"
                onSubmit={(e) => {
                  e.preventDefault();
                  void sendDialogue(dialogueInput);
                }}
              >
                <input
                  className="portal-chat__input"
                  value={dialogueInput}
                  onChange={(e) => setDialogueInput(e.target.value)}
                  placeholder={`向${dialogueChar.name}提问…`}
                  disabled={dialogueLoading}
                />
                <button type="submit" className="portal-btn portal-btn--dark" disabled={dialogueLoading}>
                  {dialogueLoading ? '…' : '发送'}
                </button>
              </form>
            </AtlasSlideIn>
          ) : (
            <AtlasSlideIn animKey="dialogue-pick">
              <p className="portal-chat__empty">请先选择一位历史人物。</p>
            </AtlasSlideIn>
          )}
        </div>
      </PortalModuleOverlay>

      <PortalModuleOverlay
        open={activeModule === 'tutor'}
        title="AI 助教"
        subtitle="知识点梳理 · 随堂答疑"
        tone="pink"
        onClose={() => setActiveModule(null)}
      >
        <div className="portal-tutor">
          <aside className="portal-tutor__sidebar">
            <h4>本章要点</h4>
            <ul>
              <li>井田与早期贡赋伦理</li>
              <li>盐铁论：国家垄断之辩</li>
              <li>两税法与税源货币化</li>
              <li>熙宁新法体系</li>
              <li>一条鞭与银粮并收</li>
            </ul>
          </aside>
          <AtlasSlideIn animKey="tutor-chat" className="portal-tutor__chat">
            <div className="portal-chat__prompts">
              {TUTOR_QUICK_PROMPTS.map((p) => (
                <button key={p} type="button" className="portal-pill portal-pill--pink" onClick={() => void sendTutor(p)}>
                  {p}
                </button>
              ))}
            </div>
            <div className="portal-chat__log">
              {tutorMessages.length === 0 ? (
                <AtlasSlideIn animKey="tutor-empty">
                  <p className="portal-chat__empty">我是课程助教，可帮你梳理概念与比较视角。</p>
                </AtlasSlideIn>
              ) : (
                tutorMessages.map((m) => (
                  <AtlasSlideIn key={m.id} animKey={m.id}>
                    <div className={`portal-chat__msg portal-chat__msg--${m.role}`}>
                      <div>{m.text}</div>
                      {m.citations && m.citations.length > 0 ? (
                        <div className="portal-tutor__refs">
                          {m.citations.map((c, j) => (
                            <span key={j} className="portal-pill portal-pill--pink portal-pill--sm">
                              {c.era ? `${c.era} · ` : ''}
                              {c.title}
                            </span>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </AtlasSlideIn>
                ))
              )}
            </div>
            <form
              className="portal-chat__form"
              onSubmit={(e) => {
                e.preventDefault();
                void sendTutor(tutorInput);
              }}
            >
              <input
                className="portal-chat__input"
                value={tutorInput}
                onChange={(e) => setTutorInput(e.target.value)}
                placeholder="输入课程相关问题…"
                disabled={tutorLoading}
              />
              <button type="submit" className="portal-btn portal-btn--dark" disabled={tutorLoading}>
                {tutorLoading ? '…' : '提问'}
              </button>
            </form>
          </AtlasSlideIn>
        </div>
      </PortalModuleOverlay>
    </div>
  );
};
