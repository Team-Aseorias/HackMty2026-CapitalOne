export interface PurchaseAttempt { customer_id: string; account_id: string; merchant: string; merchant_id?: string; amount: number }
export interface DemoPurchaseAttempt { merchant: string; amount: number }
export interface DemoProfile {
  key: string; label: string; description: string;
  resolved_verifications: number; reported_abandons: number;
  history_source: 'controlled_demo_plus_reported_session';
}
export interface Decision {
  id: string; decision: 'allow' | 'verify'; risk_score: number; reason: string;
  demo_profile_key?: string | null;
  estimated_cost_allow: number | null; estimated_cost_verify: number | null; uplift: number | null;
  allow_completion_probability: number | null; verify_completion_probability: number | null;
  incremental_abandonment_probability: number | null; safety_override: boolean; personalization_applied: boolean;
  context_source: 'nessie' | 'local'; persistence_source: 'mongo' | 'memory'; model_version: string;
  policy_version?: string;
  fraud_status?: 'unknown';
  safety_checks?: { code: string; observed: number; threshold: number; triggered: boolean }[];
  cost_preferred_action?: 'allow' | 'verify' | null;
  model_warnings?: string[];
  personalization_evidence?: { resolved_verifications: number; reported_abandons: number; smoothed_abandonment_rate: number; minimum_history: number } | null;
  recent_activity?: { window_seconds: number; prior_attempts: number; prior_verify_abandons: number } | null;
}
export type Outcome = 'pending' | 'completed' | 'abandoned';
export interface DecisionRecord extends Decision {
  customer_id?: string; account_id?: string; merchant: string; merchant_id?: string; amount: number;
  action: 'allow' | 'verify'; outcome: Outcome; created_at: string;
}
export interface Metrics { attempts: number; allowed: number; verified: number; completed: number; abandoned: number; pending: number; verification_rate: number; average_expected_cost: number | null; source: string }
export interface Policy { policy: string; expected_cost: number; verification_rate: number; legitimate_completion_rate: number; fraud_loss_per_attempt: number; safety_violations: number; cost_standard_error: number; sample_size: number; seed: number; data_source: string; model_version: string }
export async function request<T>(path: string, method = 'GET', body?: unknown, signal?: AbortSignal): Promise<T> {
  const response = await fetch('/api' + path, { method, signal, headers: { 'Content-Type': 'application/json' }, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await response.json().catch(() => null) as { detail?: string | { msg: string }[] } | null;
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((item: { msg: string }) => item.msg).join('; ') : 'No fue posible comunicarse con ANCLA.';
    throw new Error(message + ' (HTTP ' + response.status + ')');
  }
  return data as T;
}
export const evaluarCompra = (attempt: PurchaseAttempt) => request<Decision>('/purchase-attempts', 'POST', attempt);
export const obtenerPerfilesDemo = (signal?: AbortSignal) => request<DemoProfile[]>('/demo-profiles', 'GET', undefined, signal);
export const evaluarCompraPerfil = (profileKey: string, attempt: DemoPurchaseAttempt) => request<Decision>('/demo-profiles/' + encodeURIComponent(profileKey) + '/purchase-attempts', 'POST', attempt);
export const obtenerDecisionesRecientes = (signal?: AbortSignal) => request<DecisionRecord[]>('/decisions/recent?limit=25', 'GET', undefined, signal);
export const obtenerMetricas = (signal?: AbortSignal) => request<Metrics>('/dashboard/metrics', 'GET', undefined, signal);
export const evaluarPoliticas = (rows: number, seed: number) => request<Policy[]>('/evaluations/run?rows=' + rows + '&seed=' + seed, 'POST');
export const registrarResultado = (id: string, outcome: Exclude<Outcome, 'pending'>) => request<DecisionRecord>('/decisions/' + encodeURIComponent(id) + (outcome === 'completed' ? '/complete' : '/abandon'), 'POST');
export const percent = (v: number | null) => v == null ? 'No disponible' : (100 * v).toFixed(1) + '%';
export const cost = (v: number | null) => v == null ? 'No disponible' : v.toLocaleString('es-MX', { maximumFractionDigits: 2, minimumFractionDigits: 2 }) + ' u.m.';
export const outcomeLabel = (v: string) => ({ pending: 'Pendiente', completed: 'Completada (reportada)', abandoned: 'Abandonada (reportada)' }[v] ?? v);
