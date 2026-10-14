export type NationMetricKey =
  | 'treasury'
  | 'innerTreasury'
  | 'taxStability'
  | 'publicSupport'
  | 'scholarSupport'
  | 'emperorTrust'
  | 'externalPressure';

export interface NationMetric {
  key: NationMetricKey;
  label: string;
  value: number;
  trend?: 'up' | 'down' | 'stable';
}

export interface NationState {
  dynasty: string;
  reignTitle: string;
  yearLabel: string;
  metrics: NationMetric[];
}

export interface Character {
  id: string;
  name: string;
  title: string;
  faction: 'reformer' | 'conservative' | 'emperor' | 'other';
  ideologyTags: string[];
  avatarColor?: string;
  /** 可选；未设则自动读 /portraits/song|ming/{id}.png */
  avatarUrl?: string;
  /** 后端 /chat 的 character_id（renwu_module.characters.CHARACTERS） */
  apiCharacterId?: string;
  /** 是否在「问策」人物面板展示；缺省为 true（有 apiCharacterId 时） */
  consultable?: boolean;
  brief: string;
}

export interface EventOptionEffect {
  metric: NationMetricKey;
  delta: number;
}

export interface EventOption {
  id: string;
  label: string;
  description: string;
  effects: EventOptionEffect[];
  hint?: string;
}

export interface EventSpeakerLine {
  characterId: string;
  text: string;
}

export interface CourtEvent {
  id: string;
  title: string;
  summary: string;
  speakers: EventSpeakerLine[];
  options: EventOption[];
  relatedMemorialId?: string;
}

export type MemorialUrgency = 'low' | 'medium' | 'high';
export type MemorialStatus = 'unread' | 'read' | 'decided';

export interface Memorial {
  id: string;
  title: string;
  author: string;
  fromRegion: string;
  urgency: MemorialUrgency;
  status: MemorialStatus;
  abstract: string;
}

export interface LogEntry {
  id: string;
  turn: number;
  timeLabel: string;
  summary: string;
  metricChanges: EventOptionEffect[];
}

export interface MetricDeltaPreview {
  metric: NationMetricKey;
  delta: number;
  reasons: string[];
}

export type MapPointType = 'capital' | 'border' | 'taxHub' | 'event';

export interface MapPoint {
  id: string;
  name: string;
  x: number; // 0-1, 相对于背景图宽度
  y: number; // 0-1, 相对于背景图高度
  type: MapPointType;
}


