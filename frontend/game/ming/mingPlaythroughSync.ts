import { getAccessToken } from '../../lib/authStorage';
import { createPlaythrough, updatePlaythrough } from '../../lib/classroomApi';
import type { MingGameState } from './mingTurnPhase';
import type { ScenarioId } from '../scenarios';
import { buildSalvageSummaryJsonFromState } from './salvageScore';
import {
  buildSalvageTurnChapter,
  type SalvageTurnChapterOptions,
} from '../playthroughQuarterSync';

export type { SalvageTurnChapterOptions };

export async function tryCreateSalvagePlaythrough(
  scenarioId: ScenarioId,
  gameSessionId: string,
  campaignSessionId?: string,
): Promise<string> {
  if (!getAccessToken() || !gameSessionId) return '';
  try {
    const pt = await createPlaythrough({
      scenario_code: scenarioId,
      game_session_id: gameSessionId,
      campaign_session_id: campaignSessionId,
    });
    return pt.id;
  } catch {
    return '';
  }
}

export async function syncSalvagePlaythrough(
  playthroughId: string,
  st: MingGameState | undefined,
  campaignSessionId?: string,
  chapterOpts?: SalvageTurnChapterOptions,
): Promise<void> {
  if (!playthroughId || !st) return;
  const turn = Number(st.turn?.turn) || 0;
  const turnChapter = buildSalvageTurnChapter(st, chapterOpts);
  try {
    if (st.ending || st.ended) {
      await updatePlaythrough(playthroughId, {
        status: 'finished',
        current_quarter: turn,
        ending_type: st.ending?.status || 'ended',
        summary_json: buildSalvageSummaryJsonFromState(st),
        ...(turnChapter ? { quarter_chapters: [turnChapter as Record<string, unknown>] } : {}),
        campaign_session_id: campaignSessionId?.trim() || undefined,
      });
      return;
    }
    if (turn > 0) {
      await updatePlaythrough(playthroughId, {
        current_quarter: turn,
        ...(turnChapter ? { quarter_chapters: [turnChapter as Record<string, unknown>] } : {}),
        campaign_session_id: campaignSessionId?.trim() || undefined,
      });
    }
  } catch {
    /* 课堂服务不可用时继续游戏 */
  }
}
