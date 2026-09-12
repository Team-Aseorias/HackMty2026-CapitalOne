import { useRef, useState } from 'react';
import anclaLogo from '../assets/ANCLA.png';
import { cost, percent, outcomeLabel, registrarResultado, request, type DecisionRecord } from '../services/api';
import './DecisionPanel.css';
export default function DecisionPanel({ decision: d, onUpdate, onNew, onViewEvaluation, onViewFeed }: { decision: DecisionRecord; onUpdate: (d: DecisionRecord) => void; onNew: () => void; onViewEvaluation: () => void; onViewFeed: () => void }) {
  const [busy, setBusy] = useState(false);
  const pending = useRef(false);
  const [error, setError] = useState('');
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
      <span className={'decision-badge ' + d.decision}>{d.decision.toUpperCase()}</span><p>Riesgo estimado de fraude: <strong>{percent(d.risk_score)}</strong></p><p>{reason}</p>
    </section>
    <section className="comparison-section"><h2>¿Permitir o verificar?</h2><div className="options-grid">
      {(['allow', 'verify'] as const).map(action => <article className={'option-card ' + (d.decision === action ? 'selected' : '')} key={action}>
        <h3>{action === 'allow' ? 'Permitir' : 'Verificar'}</h3>{d.decision === action && <span className="recommended-tag">RECOMENDADO</span>}
        <div className="expected-cost"><span>Costo esperado</span><strong>{cost(action === 'allow' ? d.estimated_cost_allow : d.estimated_cost_verify)}</strong></div>
        <p>Probabilidad de completar si la compra es legítima: <strong>{percent(action === 'allow' ? d.allow_completion_probability : d.verify_completion_probability)}</strong></p>
      </article>)}</div>
      <p>Beneficio neto estimado de verificar (permitir − verificar): <strong>{cost(d.uplift)}</strong>. Positivo favorece verificar; negativo favorece permitir, sujeto a seguridad.</p>
      <p>Abandono incremental estimado al verificar: <strong>{d.incremental_abandonment_probability == null ? 'No disponible' : (d.incremental_abandonment_probability * 100).toFixed(1) + ' puntos porcentuales'}</strong>.</p>
    </section>
    <section className="explanation-card"><div><h2>Contexto de la recomendación</h2>
      <p>{d.personalization_applied ? 'Personalización basada en resultados históricos de verificaciones.' : 'Sin historial suficiente para aplicar personalización.'}</p>
      <p>{d.context_source === 'nessie' ? 'Contexto de cuenta consultado en Nessie.' : 'Contexto local: no se confirmó contexto en Nessie.'} {d.persistence_source === 'mongo' ? 'Decisión guardada en MongoDB.' : 'Decisión en memoria; puede perderse al reiniciar.'}</p>
      <p>Modelo {d.model_version}, entrenado con datos sintéticos. Las probabilidades de completar no son porcentajes de confianza.</p>
    </div></section>
    <section className="explanation-card"><div><h2>Resultado: {outcomeLabel(d.outcome)}</h2>
      <p>Reporta el desenlace observado en el sistema consumidor. Estos botones no ejecutan pagos ni retos de verificación.</p>
      {d.outcome === 'pending' && <div className="ancla-actions"><button disabled={busy} onClick={() => report('completed')}>Reportar compra completada</button><button disabled={busy} onClick={() => report('abandoned')}>Reportar abandono</button></div>}
      {busy && <p role="status">Guardando…</p>}{error && <p role="alert">{error}</p>}
    </div></section>
    <nav className="ancla-actions"><button onClick={onNew}>Nueva evaluación</button><button onClick={onViewFeed}>Historial</button><button onClick={onViewEvaluation}>Comparar políticas</button></nav>
  </main>;
}
