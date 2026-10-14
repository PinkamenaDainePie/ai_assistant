import type { ScenarioId } from '../scenarios';
import { getPlayerPowerId } from '../scenarios';

export type EndingUiCopy = {
  chronicleSubtitle: string;
  reviewerLabel: string;
  summaryHeading: string;
  timelineHeading: string;
};

/** Scenario-aware chrome for salvage ending modal (API supplies ending.label/summary). */
export function getEndingUiCopy(scenarioId?: ScenarioId | string | null): EndingUiCopy {
  const isSong = getPlayerPowerId(scenarioId) === 'song';
  if (isSong) {
    return {
      chronicleSubtitle: '熙宁纪事',
      reviewerLabel: '史官总评',
      summaryHeading: '盖棺论定',
      timelineHeading: '变法逐月纪',
    };
  }
  return {
    chronicleSubtitle: '大明国史馆录',
    reviewerLabel: '国史编纂官总评',
    summaryHeading: '盖棺论定',
    timelineHeading: '一朝逐月历程',
  };
}
