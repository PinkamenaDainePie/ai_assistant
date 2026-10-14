import { clearAccessToken, getAccessToken, setAccessToken } from './authStorage';

export type ClassroomUser = {
  id: string;
  email: string;
  name: string;
  role: 'student' | 'teacher' | 'admin' | string;
  org: string;
  student_id?: string | null;
};

export type AuthConfig = {
  enabled: boolean;
  allow_register: boolean;
  swufe_sso_enabled: boolean;
  allow_local_login: boolean;
};

export type PlaythroughRecord = {
  id: string;
  user_id: string;
  scenario_code: string;
  game_session_id: string;
  status: string;
  current_quarter: number;
  ending_type?: string | null;
  summary_json: Record<string, unknown>;
  started_at: string;
  finished_at?: string | null;
  student_name?: string | null;
  student_id?: string | null;
  teacher_review_score?: number | null;
  teacher_review_comment?: string | null;
  teacher_review_at?: string | null;
  quarter_chapters?: Array<Record<string, unknown>>;
};

export type ClassInfo = {
  id: number;
  name: string;
  course_name: string;
  semester: string;
};

function getBaseUrl(): string {
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env) return env.replace(/\/+$/, '');
  if (typeof window !== 'undefined') {
    return `${window.location.origin}/api/backend`.replace(/\/+$/, '');
  }
  return (process.env.BACKEND_PROXY_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
}

async function parseError(resp: Response): Promise<string> {
  try {
    const j = (await resp.json()) as { detail?: unknown };
    if (typeof j.detail === 'string') return j.detail;
    return JSON.stringify(j.detail);
  } catch {
    return resp.statusText || `HTTP ${resp.status}`;
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const base = getBaseUrl();
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json');
  }
  if (init.auth !== false) {
    const token = getAccessToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }
  let resp: Response;
  try {
    resp = await fetch(`${base}${path}`, { ...init, headers });
  } catch {
    throw new Error(
      `无法连接后端 API（${base}）。请确认主 API 已在 8000 端口启动，或改用 Next 代理 /api/backend`,
    );
  }
  if (!resp.ok) {
    throw new Error(await parseError(resp));
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

export async function fetchAuthConfig(): Promise<AuthConfig> {
  return request<AuthConfig>('/api/auth/config', { auth: false });
}

export async function login(email: string, password: string): Promise<ClassroomUser> {
  const out = await request<{ access_token: string; user: ClassroomUser }>('/api/auth/login', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ email, password }),
  });
  setAccessToken(out.access_token);
  return out.user;
}

export async function register(payload: {
  email: string;
  password: string;
  name: string;
  student_id?: string;
}): Promise<ClassroomUser> {
  await request<ClassroomUser>('/api/auth/register', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({
      email: payload.email,
      password: payload.password,
      name: payload.name,
      role: 'student',
      student_id: payload.student_id || undefined,
    }),
  });
  return login(payload.email, payload.password);
}

export function logout(): void {
  clearAccessToken();
}

export function getSwufeSsoStartUrl(): string {
  return `${getBaseUrl()}/api/auth/sso/swufe/start`;
}

export function getSwufeSsoMockUrl(role: 'student' | 'teacher' = 'student'): string {
  return `${getBaseUrl()}/api/auth/sso/swufe/mock?role=${role}`;
}

export async function completeSsoCallback(accessToken: string): Promise<ClassroomUser> {
  setAccessToken(accessToken);
  return fetchMe();
}

export async function fetchMe(): Promise<ClassroomUser> {
  return request<ClassroomUser>('/api/me');
}

export async function createPlaythrough(payload: {
  scenario_code: string;
  game_session_id: string;
  campaign_session_id?: string;
}): Promise<PlaythroughRecord> {
  return request<PlaythroughRecord>('/api/playthroughs', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updatePlaythrough(
  id: string,
  payload: {
    status?: string;
    current_quarter?: number;
    ending_type?: string;
    summary_json?: Record<string, unknown>;
    campaign_session_id?: string;
    quarter_chapters?: Array<Record<string, unknown>>;
  },
): Promise<PlaythroughRecord> {
  return request<PlaythroughRecord>(`/api/playthroughs/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}

export async function fetchMyPlaythroughs(): Promise<PlaythroughRecord[]> {
  const out = await request<{ items: PlaythroughRecord[] }>('/api/playthroughs/mine');
  return out.items;
}

export async function fetchTeacherClasses(): Promise<ClassInfo[]> {
  return request<ClassInfo[]>('/api/teacher/classes');
}

export async function fetchTeacherPlaythroughs(params?: {
  class_id?: number;
  scenario_code?: string;
  status?: string;
}): Promise<PlaythroughRecord[]> {
  const q = new URLSearchParams();
  if (params?.class_id != null) q.set('class_id', String(params.class_id));
  if (params?.scenario_code) q.set('scenario_code', params.scenario_code);
  if (params?.status) q.set('status', params.status);
  const qs = q.toString();
  const out = await request<{ items: PlaythroughRecord[] }>(
    `/api/teacher/playthroughs${qs ? `?${qs}` : ''}`,
  );
  return out.items;
}

export async function fetchTeacherPlaythrough(id: string): Promise<PlaythroughRecord> {
  return request<PlaythroughRecord>(`/api/teacher/playthroughs/${id}`);
}

export async function updateTeacherPlaythroughReview(
  id: string,
  payload: { score: number; comment?: string },
): Promise<PlaythroughRecord> {
  return request<PlaythroughRecord>(`/api/teacher/playthroughs/${id}/review`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  });
}
