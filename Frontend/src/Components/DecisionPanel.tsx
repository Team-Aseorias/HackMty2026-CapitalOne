import { useRef, useState } from 'react';
import anclaLogo from '../assets/ANCLA.png';
import { cost, percent, outcomeLabel, registrarResultado, request, type DecisionRecord } from '../services/api';
import './DecisionPanel.css';
import { probability, safetyExplanation } from '../services/explanation';
export default function DecisionPanel({ decision: d, onUpdate, onNew, onViewEvaluation, onViewFeed }: { decision: DecisionRecord; onUpdate: (d: DecisionRecord) => void; onNew: () => void; onViewEvaluation: () => void; onViewFeed: () => void }) {
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [error, setError] = useState('');
  const triggeredChecks = d.safety_checks?.filter(check => check.triggered) ?? [];
  const evidence = d.personalization_evidence;
  const activity = d.recent_activity;
  const outsideTraining = d.model_warnings?.filter(w => w.startsWith('outside_training_range:')) ?? [];
  async function report(outcome: 'completed' | 'abandoned') {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try { onUpdate(await registrarResultado(d.id, outcome)); }
    catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo registrar el resultado.');
      try { onUpdate(await request<DecisionRecord>('/decisions/' + encodeURIComponent(d.id))); } catch { /* Never assume success after a network failure. */ }
    } finally { pending.current = false; setBusy(false); }
  }
  const reason = d.safety_override ? 'Se activó un límite de riesgo, pérdida potencial, importe o disponibilidad de contexto. La seguridad tiene prioridad sobre el costo estimado.'
    : d.estimated_cost_allow == null || d.estimated_cost_verify == null ? 'No hay estimaciones causales disponibles; se recomienda verificar.'
    : d.decision === 'verify' ? 'Verificar tiene menor costo esperado al considerar fraude y fricción.' : 'El beneficio de verificar no compensa su costo de fricción.';
  return <main className="decision-page">
    <header className="decision-header"><img src={anclaLogo} alt="ANCLA" height="85" /><span className="decision-id">Decisión {d.id}</span></header>
    <section className="purchase-summary"><div><span>Comercio</span><strong>{d.merchant}</strong></div><div><span>Importe</span><strong>{cost(d.amount)}</strong></div></section>
    <section className="recommendation-card"><span className="section-label">RECOMENDACIÓN DEL MOTOR</span>
      <h1>{d.decision === 'verify' ? 'Solicitar verificación' : 'Continuar sin verificación adicional'}</h1>
      <span className={'decision-badge ' + d.decision}>{d.decision.toUpperCase()}</span><p>Riesgo estimado de fraude: <strong>{probability(d.risk_score)}</strong></p><p>{reason}</p>
      {triggeredChecks.length > 0 && <ul>{triggeredChecks.map(check => <li key={check.code}>{safetyExplanation(check)}</li>)}</ul>}
      {d.safety_override && d.cost_preferred_action === 'allow' && <p>La comparación económica favorece permitir, pero la política recomienda verificar por las reglas anteriores. El abandono no desactiva estos límites.</p>}
      {outsideTraining.length > 0 && <p role="alert">Hay características fuera del rango de entrenamiento. Los números siguientes son extrapolaciones, no estimaciones validadas para este perfil.</p>}
    </section>
    <section className="comparison-section"><h2>¿Permitir o verificar?</h2><div className="options-grid">
      {(['allow', 'verify'] as const).map(action => <article className={'option-card ' + (d.decision === action ? 'selected' : '')} key={action}>
        <h3>{action === 'allow' ? 'Permitir' : 'Verificar'}</h3>{d.decision === action && <span className="recommended-tag">RECOMENDADO</span>}
        <div className="expected-cost"><span>Costo esperado</span><strong>{cost(action === 'allow' ? d.estimated_cost_allow : d.estimated_cost_verify)}</strong></div>
        <p>Probabilidad de completar si la compra es legítima: <strong>{probability(action === 'allow' ? d.allow_completion_probability : d.verify_completion_probability)}</strong></p>
        {action === 'allow' && <p>El simulador supone que una compra legítima sin verificación se completa. Este valor no significa ausencia de fraude.</p>}
      </article>)}</div>
      <p>Beneficio neto estimado de verificar (permitir − verificar): <strong>{cost(d.uplift)}</strong>. Positivo favorece verificar; negativo favorece permitir, sujeto a seguridad.</p>
      <p>Abandono incremental estimado al verificar: <strong>{d.incremental_abandonment_probability == null ? 'No disponible' : (d.incremental_abandonment_probability * 100).toFixed(1) + ' puntos porcentuales'}</strong>.</p>
    </section>
    <section className="explanation-card"><div><h2>Contexto de la recomendación</h2>
      <p>{d.personalization_applied ? 'Personalización basada en resultados históricos de verificaciones.' : 'Sin historial suficiente para aplicar personalización.'}</p>
      {evidence && <p>Historial usado: {evidence.resolved_verifications} verificaciones con resultado, {evidence.reported_abandons} abandonos reportados. Tasa histórica suavizada: {percent(evidence.smoothed_abandonment_rate)}; mínimo de {evidence.minimum_history} resultados para incorporar la tasa personal. Esta tasa es una entrada al modelo, no la probabilidad predicha de abandonar la compra actual.</p>}
      {activity ? <p>Últimos {activity.window_seconds / 60} minutos: {activity.prior_attempts} intentos anteriores y {activity.prior_verify_abandons} abandonos de verificaciones reportados. Las ráfagas activan reglas de precaución; no se convierten en un porcentaje inventado de fraude.</p> : <p>Esta decisión no tiene un análisis de frecuencia registrado.</p>}
      <p>{d.context_source === 'nessie' ? 'Contexto de cuenta consultado en Nessie.' : 'Contexto local: no se confirmó contexto en Nessie.'} {d.persistence_source === 'mongo' ? 'Decisión guardada en MongoDB.' : 'Decisión en memoria; puede perderse al reiniciar.'}</p>
      <p>Modelo {d.model_version}, entrenado con datos sintéticos. Las probabilidades de completar no son porcentajes de confianza.</p>
    </div></section>
    <section className="explanation-card"><div><h2>Resultado: {outcomeLabel(d.outcome)}</h2>
      <p>Reporta el desenlace observado en el sistema consumidor. Estos botones no ejecutan pagos ni retos de verificación.</p>
      <p>Estado de fraude: desconocido. “Completada” no confirma que sea legítima y “abandonada” no confirma fraude. Estos reportes no reentrenan el predictor de fraude.</p>
      {d.outcome === 'pending' && <div className="ancla-actions"><button disabled={busy} onClick={() => report('completed')}>Reportar compra completada</button><button disabled={busy} onClick={() => report('abandoned')}>Reportar abandono</button></div>}
      {busy && <p role="status">Guardando…</p>}{error && <p role="alert">{error}</p>}
    </div></section>
    <nav className="ancla-actions"><button onClick={onNew}>Nueva evaluación</button><button onClick={onViewFeed}>Historial</button><button onClick={onViewEvaluation}>Comparar políticas</button></nav>
  </main>;
}
