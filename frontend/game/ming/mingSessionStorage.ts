import type { ScenarioId } from '../scenarios';
import { resolveSalvageScenarioId } from '../scenarios';

const LEGACY_MING_SESSION_KEY = 'ming_salvage_session_active';
const SALVAGE_SESSION_KEY = 'salvage_session';

export interface SalvageSessionPersist {
  scenarioId: ScenarioId;
  salvageScenarioId: string;
  savedAt: number;
  playthroughId?: string;
}

export function persistSalvageSession(scenarioId: ScenarioId, playthroughId?: string): void {
  if (typeof window === 'undefined') return;
  const prev = readSalvageSession();
  const payload: SalvageSessionPersist = {
    scenarioId,
    salvageScenarioId: resolveSalvageScenarioId(scenarioId),
    savedAt: Date.now(),
    playthroughId: playthroughId || prev?.playthroughId,
  };
  try {
    localStorage.setItem(SALVAGE_SESSION_KEY, JSON.stringify(payload));
    localStorage.removeItem(LEGACY_MING_SESSION_KEY);
  } catch {
    /* ignore quota / private mode */
  }
}

/** @deprecated 使用 persistSalvageSession */
export function persistMingSessionActive(): void {
  persistSalvageSession('ming_wanli');
}

export function readSalvageSession(): SalvageSessionPersist | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(SALVAGE_SESSION_KEY);
    if (raw) {
      const data = JSON.parse(raw) as Partial<SalvageSessionPersist>;
      if (data.scenarioId && data.salvageScenarioId) {
        return {
          scenarioId: data.scenarioId as ScenarioId,
          salvageScenarioId: String(data.salvageScenarioId),
          savedAt: Number(data.savedAt) || 0,
        };
      }
    }
    if (localStorage.getItem(LEGACY_MING_SESSION_KEY) === '1') {
      return {
        scenarioId: 'ming_wanli',
        salvageScenarioId: 'ming_wanli',
        savedAt: 0,
      };
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function clearSalvageSessionPersist(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(SALVAGE_SESSION_KEY);
    localStorage.removeItem(LEGACY_MING_SESSION_KEY);
  } catch {
    /* ignore */
  }
}

/** @deprecated 使用 clearSalvageSessionPersist */
export function clearMingSessionPersist(): void {
  clearSalvageSessionPersist();
}

export function isSalvageSessionPersisted(): boolean {
  return readSalvageSession() !== null;
}

/** @deprecated 使用 isSalvageSessionPersisted */
export function isMingSessionPersisted(): boolean {
  return isSalvageSessionPersisted();
}
