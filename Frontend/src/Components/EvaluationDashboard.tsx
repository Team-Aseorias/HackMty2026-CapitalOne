import { useEffect, useRef, useState } from 'react';
import { cost, percent, obtenerMetricas, evaluarPoliticas, type Metrics, type Policy } from '../services/api';
import './EvaluationDashboard.css';
const names: Record<string, string> = { fixed_rule: 'Regla fija (importe ≥ 500)', predictive: 'Predictiva con límites de seguridad', causal: 'ANCLA con seguridad', causal_unconstrained: 'Causal sin límites (experimental)', causal_unpersonalized: 'Causal sin personalización' };
export default function EvaluationDashboard({ onBack }: { onBack: () => void }) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [metricError, setMetricError] = useState('');
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [rows, setRows] = useState(1250);
  const [seed, setSeed] = useState(2027);
  const [busy, setBusy] = useState(false);
  const running = useRef(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    obtenerMetricas(controller.signal).then(setMetrics).catch(err => { if (!controller.signal.aborted) setMetricError(err.message); });
    return () => controller.abort();
  }, []);
  async function run() {
    if (running.current) return;
    running.current = true; setBusy(true); setError(''); setPolicies([]);
    try { setPolicies(await evaluarPoliticas(rows, seed)); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo evaluar.'); }
    finally { running.current = false; setBusy(false); }
  }
  const eligible = policies.filter(p => p.safety_violations === 0);
  const best = eligible.length ? Math.min(...eligible.map(p => p.expected_cost)) : null;
  return <main className="evaluation-page">
    <header className="evaluation-header"><h1>Seguridad, costo y fricción</h1><button className="back-button" onClick={onBack}>Volver</button></header>
    <section className="operation-section"><h2>Operación registrada</h2><p>Totales disponibles al abrir esta pantalla; independientes de la evaluación sintética.</p>
      {metricError && <p role="alert">{metricError}</p>}{!metrics && !metricError && <p role="status">Cargando métricas…</p>}
      {metrics && <><div className="operation-grid">
        {[['Decisiones', metrics.attempts], ['Permitir / verificar', metrics.allowed + ' / ' + metrics.verified], ['Completadas / abandonadas', metrics.completed + ' / ' + metrics.abandoned], ['Pendientes', metrics.pending], ['Tasa de verificación recomendada', percent(metrics.verification_rate)], ['Costo esperado medio', cost(metrics.average_expected_cost)]].map(([label, value]) => <article className="operation-card" key={label}><span>{label}</span><strong>{value}</strong></article>)}
      </div><p>Fuente: {metrics.source === 'mongo' ? 'MongoDB' : 'memoria temporal'}. “Completadas” significa compras reportadas, no verificaciones aprobadas.</p></>}
    </section>
    <section className="evaluation-section"><h2>Comparación reproducible de políticas</h2>
      <p>Buscamos menor costo esperado respetando límites de seguridad. Eso puede requerir más verificaciones. Los resultados provienen de un simulador, no de pérdidas bancarias reales.</p>
      <form className="ancla-actions" onSubmit={e => { e.preventDefault(); void run(); }}>
        <label>Casos <input type="number" min="100" max="10000" step="1" required disabled={busy} value={rows} onChange={e => setRows(Number(e.target.value))} /></label>
        <label>Semilla de prueba <input type="number" min="2027" step="1" required disabled={busy} value={seed} onChange={e => setSeed(Number(e.target.value))} /></label>
        <button disabled={busy}>{busy ? 'Evaluando…' : 'Ejecutar evaluación sintética'}</button>
      </form>
      {error && <p role="alert">{error}</p>}
      {policies.length > 0 && <>
        <p>{policies[0].sample_size} casos · semilla {policies[0].seed} · modelo {policies[0].model_version}. Menor media observada entre políticas sin violaciones: {eligible.length ? eligible.filter(p => p.expected_cost === best).map(p => names[p.policy] ?? p.policy).join(', ') : 'Ninguna elegible'}. Esto no demuestra superioridad estadística.</p>
        <div className="policy-table-wrap"><table className="policy-table"><thead><tr><th>Política</th><th>Costo medio / intento</th><th>Error estándar</th><th>Pérdida por fraude / intento</th><th>Finalización legítima</th><th>Verificaciones</th><th>Violaciones de seguridad</th></tr></thead>
        <tbody>{policies.map(p => <tr key={p.policy} className={p.policy === 'causal' ? 'recommended-row' : ''}>
          <td>{names[p.policy] ?? p.policy}</td><td>{cost(p.expected_cost)}</td><td>{cost(p.cost_standard_error)}</td><td>{cost(p.fraud_loss_per_attempt)}</td><td>{percent(p.legitimate_completion_rate)}</td><td>{percent(p.verification_rate)}</td><td>{p.safety_violations}</td>
        </tr>)}</tbody></table></div>
        <p>La finalización legítima se calcula solamente sobre compras legítimas. Las variantes experimentales permiten comparar el efecto de los límites y la personalización; la política servida es “ANCLA con seguridad”.</p>
      </>}
    </section>
  </main>;
}
