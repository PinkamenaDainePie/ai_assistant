'use client';

import React, { useMemo, useState } from 'react';
import type { QuarterChapterRecord } from '../../game/quarterChapterArchive';
import {
  buildQuarterChapterListItems,
  resolveQuarterChapterDetail,
  type QuarterChapterListItem,
} from '../../game/quarterChapterDisplay';
import type { ScenarioId } from '../../game/scenarios';

type Props = {
  quarterChapters?: Array<Record<string, unknown>> | null;
  scenarioCode: string;
  currentQuarter: number;
  status: string;
};

function toChapterRecords(
  raw?: Array<Record<string, unknown>> | null,
): QuarterChapterRecord[] {
  if (!Array.isArray(raw)) return [];
  return (raw.filter(Boolean) as QuarterChapterRecord[]).filter((ch) => {
    if (ch.narrative_mode === 'salvage_monthly') {
      return Boolean(
        String(ch.body_zh || ch.edict_text || ch.summary_zh || ch.headline_zh || '').trim(),
      );
    }
    return Boolean(
      String(ch.body_zh || ch.summary_zh || ch.headline_zh || ch.edict_text || '').trim(),
    );
  });
}

function emptyHint(status: string, currentQuarter: number): string {
  if (currentQuarter <= 0) return '该生尚未开始游玩。';
  if (status === 'in_progress') {
    return '暂无归档的季度总结；学生需至少完成一季结算后，本处将显示朝政纪要与诏书。';
  }
  return '本局未产生可展示的季度总结或诏书。';
}

export function PlaythroughQuarterTimelinePanel({
  quarterChapters,
  scenarioCode,
  currentQuarter,
  status,
}: Props) {
  const chapters = useMemo(() => toChapterRecords(quarterChapters), [quarterChapters]);
  const scenarioId = (scenarioCode || null) as ScenarioId | null;
  const items = useMemo(
    () =>
      buildQuarterChapterListItems(chapters, {
        scenarioId,
        currentQuarter,
      }),
    [chapters, scenarioId, currentQuarter],
  );

  const [activeId, setActiveId] = useState<string>('');
  const selectedId = activeId || items[0]?.id || '';
  const detail = resolveQuarterChapterDetail(selectedId, chapters, {
    scenarioId,
    currentQuarter,
  });

  const handleSelect = (item: QuarterChapterListItem) => {
    setActiveId(item.id);
  };

  return (
    <section className="ui-panel">
      <div className="ui-panel__head">
        <h2 className="ui-panel__title">过程时间轴</h2>
        <span className="ui-muted">季度总结与诏书</span>
      </div>

      {items.length === 0 ? (
        <p className="ui-muted ui-panel__body">{emptyHint(status, currentQuarter)}</p>
      ) : (
        <div className="ui-quarter-timeline">
          <ul className="ui-quarter-timeline__list">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={
                    item.id === selectedId
                      ? 'ui-quarter-timeline__item ui-quarter-timeline__item--active'
                      : 'ui-quarter-timeline__item'
                  }
                  onClick={() => handleSelect(item)}
                >
                  <span className="ui-quarter-timeline__label">{item.quarterLabel}</span>
                  <span className="ui-quarter-timeline__title">{item.title}</span>
                  <span className="ui-quarter-timeline__abstract">{item.abstract}</span>
                </button>
              </li>
            ))}
          </ul>

          {detail ? (
            <article className="ui-quarter-timeline__detail">
              <header className="ui-quarter-timeline__detail-head">
                <h3>{detail.title}</h3>
                <p className="ui-muted">{detail.quarterLabel}</p>
                {detail.headline ? <p className="ui-quarter-timeline__headline">{detail.headline}</p> : null}
              </header>
              <div className="ui-quarter-timeline__body">{detail.body}</div>
              {detail.sections.map((section) => (
                <div key={section.title} className="ui-quarter-timeline__section">
                  <h4>{section.title}</h4>
                  {section.lines.map((line, idx) => (
                    <p key={`${section.title}-${idx}`}>{line}</p>
                  ))}
                </div>
              ))}
            </article>
          ) : null}
        </div>
      )}
    </section>
  );
}
