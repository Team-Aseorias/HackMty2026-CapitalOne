import { useEffect, useState } from 'react';
import { obtenerDecisionesRecientes, outcomeLabel, cost, type DecisionRecord } from '../services/api';
import './FeedReciente.css';
export default function FeedReciente({ onBack, onSelect }: { onBack: () => void; onSelect: (record: DecisionRecord) => void }) {
  const [records, setRecords] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try { setRecords(await obtenerDecisionesRecientes(controller.signal)); setError(''); }
      catch (err) { if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'No se pudo actualizar.'); }
      finally { if (!controller.signal.aborted) { setLoading(false); timer = setTimeout(refresh, 5000); } }
    }
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  return <main className="feed-page"><header className="feed-header"><h1>Historial de decisiones</h1><button className="back-button" onClick={onBack}>Volver</button></header>
    <p>Últimas 25 decisiones, actualizadas cada 5 segundos. La recomendación y el desenlace son datos distintos.</p>
    {loading && <p role="status">Cargando…</p>}{error && <p role="alert">{error} Los datos visibles pueden estar desactualizados.</p>}
    {!loading && !error && records.length === 0 && <p>Todavía no hay decisiones registradas.</p>}
    <ul className="feed-lista">{records.map(d => <li className="feed-item" key={d.id}><div className="feed-item-info">
      <strong>{d.merchant} · {cost(d.amount)}</strong><span>{new Date(d.created_at).toLocaleString('es-MX')} · {d.id}</span>
      <span>Recomendación: {(d.action ?? d.decision).toUpperCase()} · Resultado: {outcomeLabel(d.outcome)}</span><span>{d.persistence_source === 'mongo' ? 'Persistido' : 'En memoria'}</span>
    </div><button onClick={() => onSelect(d)}>Ver detalle / reportar resultado</button></li>)}</ul>
  </main>;
}
