'use client';



import React, { useEffect, useMemo, useRef, useState } from 'react';

import { useGameStore } from '../game/store';

import { buildQuarterChapterListItems } from '../game/quarterChapterDisplay';



const EXIT_MS = 280;



export const MemorialListDrawer: React.FC = () => {

  const {

    ui,

    quarterChapters,

    scenarioId,

    currentQuarter,
    latestQuarterReport,
    closeMemorialDrawer,
    openQuarterChapterDetail,
  } = useGameStore((s) => ({
    ui: s.ui,
    quarterChapters: s.quarterChapters,
    scenarioId: s.scenarioId,
    currentQuarter: s.currentQuarter,
    latestQuarterReport: s.latestQuarterReport,
    closeMemorialDrawer: s.closeMemorialDrawer,
    openQuarterChapterDetail: s.openQuarterChapterDetail,
  }));

  const chapterItems = useMemo(
    () =>
      buildQuarterChapterListItems(quarterChapters, {
        scenarioId,
        currentQuarter,
        latestReport: latestQuarterReport,
      }),
    [quarterChapters, scenarioId, currentQuarter, latestQuarterReport],
  );



  const isOpen = ui.isMemorialDrawerOpen;

  const [visible, setVisible] = useState(isOpen);

  const [exiting, setExiting] = useState(false);

  const exitTimerRef = useRef<number | null>(null);

  const leaveTimerRef = useRef<number | null>(null);



  useEffect(() => {

    if (isOpen) {

      if (exitTimerRef.current) window.clearTimeout(exitTimerRef.current);

      setVisible(true);

      setExiting(false);

      return;

    }

    if (!visible) return;

    setExiting(true);

    exitTimerRef.current = window.setTimeout(() => {

      setVisible(false);

      setExiting(false);

    }, EXIT_MS);

  }, [isOpen, visible]);



  useEffect(

    () => () => {

      if (exitTimerRef.current) window.clearTimeout(exitTimerRef.current);

      if (leaveTimerRef.current) window.clearTimeout(leaveTimerRef.current);

    },

    [],

  );



  const scheduleClose = () => {

    if (!isOpen || exiting || ui.isQuarterChapterDetailOpen) return;

    if (leaveTimerRef.current) window.clearTimeout(leaveTimerRef.current);

    leaveTimerRef.current = window.setTimeout(() => {

      closeMemorialDrawer();

    }, 120);

  };



  const cancelScheduledClose = () => {

    if (leaveTimerRef.current) {

      window.clearTimeout(leaveTimerRef.current);

      leaveTimerRef.current = null;

    }

  };



  if (!visible) return null;



  return (

    <div

      className={`memorial-drawer ${exiting ? 'panel-exit-left' : 'panel-enter-left'}`}

      onMouseEnter={cancelScheduledClose}

      onMouseLeave={scheduleClose}

      style={{

        position: 'fixed',

        left: 0,

        top: 0,

        bottom: 0,

        width: 360,

        background: 'linear-gradient(180deg, #1a1010 0, #0a0708 100%)',

        borderRight: '1px solid rgba(255,215,0,0.4)',

        color: '#f5f5f5',

        zIndex: 150,

        boxShadow: '4px 0 16px rgba(0,0,0,0.6)',

        display: 'flex',

        flexDirection: 'column',

      }}

    >

      <div

        style={{

          padding: '12px 16px',

          borderBottom: '1px solid rgba(255,215,0,0.3)',

          display: 'flex',

          justifyContent: 'space-between',

          alignItems: 'center',

        }}

      >

        <div style={{ fontWeight: 700, color: '#ffd700' }}>季度总结</div>

        <button

          type="button"

          onClick={() => {

            cancelScheduledClose();

            closeMemorialDrawer();

          }}

          style={{

            background: 'transparent',

            border: 'none',

            color: '#f5f5f5',

            cursor: 'pointer',

            fontSize: 14,

          }}

        >

          收起

        </button>

      </div>

      <div

        className="memorial-drawer__scroll"

        style={{

          flex: 1,

          overflowY: 'auto',

          padding: '8px 12px',

        }}

      >

        {chapterItems.length === 0 ? (

          <div

            style={{

              padding: '24px 12px',

              fontSize: 13,

              lineHeight: 1.7,

              color: '#a8a098',

              textAlign: 'center',

            }}

          >

            暂无季度总结。

            <br />

            完成「下季」推进后，AI 生成的朝政纪要将归档于此。

          </div>

        ) : (

          chapterItems.map((item) => (

            <button

              key={item.id}

              type="button"

              onClick={() => openQuarterChapterDetail(item.id)}

              style={{

                width: '100%',

                textAlign: 'left',

                padding: 10,

                marginBottom: 8,

                borderRadius: 8,

                border:

                  ui.selectedQuarterChapterId === item.id

                    ? '1px solid rgba(255,215,0,0.8)'

                    : '1px solid rgba(255,215,0,0.25)',

                background:

                  ui.selectedQuarterChapterId === item.id

                    ? 'rgba(255,215,0,0.08)'

                    : 'rgba(0,0,0,0.4)',

                cursor: 'pointer',

                fontSize: 13,

                color: 'inherit',

              }}

            >

              <div

                style={{

                  fontSize: 11,

                  color: '#c8a860',

                  marginBottom: 4,

                  letterSpacing: '0.06em',

                }}

              >

                {item.quarterLabel}

              </div>

              <div

                style={{

                  marginBottom: 4,

                  color: '#ffebc1',

                  fontWeight: 600,

                  lineHeight: 1.45,

                }}

              >

                {item.title}

              </div>

              <div

                style={{

                  fontSize: 12,

                  color: '#ccc',

                  lineHeight: 1.55,

                }}

              >

                {item.abstract}

              </div>

            </button>

          ))

        )}

      </div>

    </div>

  );

};

