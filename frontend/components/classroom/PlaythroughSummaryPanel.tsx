'use client';

import React, { useMemo, useState } from 'react';
import { parsePlaythroughSummary } from '../../lib/playthroughSummary';

type Props = {
  summaryJson: Record<string, unknown>;
  status: string;
  /** 进行中 / 无摘要时的提示 */
  emptyHint?: string;
  /** 教师端可展开原始 JSON */
  allowRawJson?: boolean;
};

export function PlaythroughSummaryPanel({
  summaryJson,
  status,
  emptyHint = '本局尚未产生终局摘要；学生完成战役后将在此显示评分与总结。',
  allowRawJson = false,
}: Props) {
  const [showRaw, setShowRaw] = useState(false);
  const parsed = useMemo(() => parsePlaythroughSummary(summaryJson), [summaryJson]);

  if (!parsed.hasContent) {
    return (
      <div className="ui-playthrough-report ui-playthrough-report--empty">
        <p className="ui-muted">{status === 'finished' ? '已完成，但终局摘要为空。' : emptyHint}</p>
      </div>
    );
  }

  return (
    <div className="ui-playthrough-report">
      {parsed.score != null ? (
        <div className="ui-playthrough-report__score">
          <span className="ui-playthrough-report__score-num">{parsed.score}</span>
          {parsed.scoreLabelZh ? (
            <span className="ui-playthrough-report__score-label">{parsed.scoreLabelZh}</span>
          ) : null}
        </div>
      ) : null}

      {parsed.titleZh ? <h3 className="ui-playthrough-report__title">{parsed.titleZh}</h3> : null}

      {(parsed.kind || parsed.endingMode) && (
        <p className="ui-playthrough-report__meta">
          {[parsed.kind, parsed.endingMode].filter(Boolean).join(' · ')}
        </p>
      )}

      {parsed.summaryZh ? (
        <p className="ui-playthrough-report__summary">{parsed.summaryZh}</p>
      ) : null}

      {parsed.highlightsZh.length > 0 ? (
        <section className="ui-playthrough-report__block">
          <h4 className="ui-playthrough-report__heading">本局亮点</h4>
          <ul className="ui-playthrough-report__list">
            {parsed.highlightsZh.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {parsed.sections.map((section) => (
        <section key={section.label} className="ui-playthrough-report__block">
          <h4 className="ui-playthrough-report__heading">{section.label}</h4>
          <p className="ui-playthrough-report__text">{section.text}</p>
        </section>
      ))}

      {parsed.historyCompareZh ? (
        <section className="ui-playthrough-report__block ui-playthrough-report__block--compare">
          <h4 className="ui-playthrough-report__heading">历史对照</h4>
          <p className="ui-playthrough-report__text">{parsed.historyCompareZh}</p>
        </section>
      ) : null}

      {allowRawJson ? (
        <div className="ui-playthrough-report__raw">
          <button
            type="button"
            className="ui-btn ui-btn--ghost ui-btn--sm"
            onClick={() => setShowRaw((v) => !v)}
          >
            {showRaw ? '隐藏原始 JSON' : '查看原始 JSON'}
          </button>
          {showRaw ? (
            <pre className="ui-code-block">{JSON.stringify(summaryJson || {}, null, 2)}</pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
