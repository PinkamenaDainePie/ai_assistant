import React from 'react';
import {
  buildCampaignMetricSummaryRows,
  buildEndingChapterTableRows,
  formatMetricDelta,
  type EndingChapterRow,
  type MetricSummaryRow,
} from '../game/endingReportDisplay';
import type { QuarterChapterRecord } from '../game/quarterChapterArchive';
import type { NationMetricKey, NationState } from '../game/types';
import type { ScenarioId } from '../game/scenarios';

type EndingReportTablesProps = {
  nationState: NationState;
  openingMetrics: Partial<Record<NationMetricKey, number>>;
  quarterChapters: QuarterChapterRecord[];
  scenarioId?: ScenarioId | null;
  currentQuarter?: number;
  latestReport?: Record<string, unknown> | null;
  highlightsZh?: string[];
};

function MetricTable({ rows }: { rows: MetricSummaryRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="ending-report-block">
      <div className="ending-report-block__title">全程数值</div>
      <div className="ending-report-table-wrap">
        <table className="ending-report-table">
          <thead>
            <tr>
              <th>指标</th>
              <th>开局</th>
              <th>终局</th>
              <th>变化</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{row.opening}</td>
                <td>{row.final}</td>
                <td
                  className={
                    row.delta > 0
                      ? 'ending-report-table__delta--up'
                      : row.delta < 0
                        ? 'ending-report-table__delta--down'
                        : undefined
                  }
                >
                  {formatMetricDelta(row.delta)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ChapterTable({ rows }: { rows: EndingChapterRow[] }) {
  if (rows.length === 0) return null;
  return (
    <div className="ending-report-block">
      <div className="ending-report-block__title">本局季次回顾</div>
      <div className="ending-report-table-wrap">
        <table className="ending-report-table ending-report-table--chapters">
          <thead>
            <tr>
              <th>季次</th>
              <th>纪年</th>
              <th>标题</th>
              <th>摘要</th>
              <th>要点</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>第 {row.quarterIndex} 季</td>
                <td>{row.quarterLabel}</td>
                <td>{row.title}</td>
                <td className="ending-report-table__abstract">{row.abstract}</td>
                <td className="ending-report-table__highlights">{row.highlights}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export const EndingReportTables: React.FC<EndingReportTablesProps> = ({
  nationState,
  openingMetrics,
  quarterChapters,
  scenarioId,
  currentQuarter,
  latestReport,
  highlightsZh,
}) => {
  const metricRows = buildCampaignMetricSummaryRows(openingMetrics, nationState);
  const chapterRows = buildEndingChapterTableRows(quarterChapters, {
    scenarioId,
    currentQuarter,
    latestReport,
  });
  const endingHighlights = (highlightsZh || []).map((s) => String(s || '').trim()).filter(Boolean);

  if (metricRows.length === 0 && chapterRows.length === 0 && endingHighlights.length === 0) {
    return null;
  }

  return (
    <div className="ending-report-tables">
      <MetricTable rows={metricRows} />
      <ChapterTable rows={chapterRows} />
      {endingHighlights.length > 0 ? (
        <div className="ending-report-block">
          <div className="ending-report-block__title">史官评点</div>
          <ul className="ending-report-highlights">
            {endingHighlights.map((line, i) => (
              <li key={`hl-${i}`}>{line}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
};
