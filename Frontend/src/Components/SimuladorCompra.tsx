import { useEffect, useRef, useState, type FormEvent } from 'react';
import { evaluarCompraPerfil, obtenerPerfilesDemo, type DecisionRecord, type DemoProfile } from '../services/api';
import './SimuladorCompra.css';
export default function SimuladorCompra({ onComprar, initial }: { onComprar: (record: DecisionRecord) => void; initial?: DecisionRecord }) {
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);
  const [error, setError] = useState('');
  const [profiles, setProfiles] = useState<DemoProfile[]>([]);
  const [profileKey, setProfileKey] = useState(initial?.demo_profile_key ?? '');
  useEffect(() => {
    const controller = new AbortController();
    obtenerPerfilesDemo(controller.signal).then(items => {
      setProfiles(items);
      setProfileKey(current => current || items[0]?.key || '');
    }).catch(err => {
      if (!controller.signal.aborted) setError(err instanceof Error ? err.message : 'No se pudieron cargar los perfiles.');
    });
    return () => controller.abort();
  }, []);
  const selected = profiles.find(profile => profile.key === profileKey);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    const data = new FormData(event.currentTarget);
    const attempt = { merchant: String(data.get('merchant')).trim(), amount: Number(data.get('amount')) };
    if (!profileKey) { setError('Selecciona un perfil de demostración.'); return; }
    busy.current = true; setLoading(true); setError('');
    try { const decision = await evaluarCompraPerfil(profileKey, attempt); onComprar({ ...attempt, ...decision, action: decision.decision, outcome: 'pending', created_at: new Date().toISOString() }); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo evaluar.'); }
    finally { busy.current = false; setLoading(false); }
  }
  return <div className="simulador-card"><h2 className="simulador-titulo">Evaluar una compra</h2>
    <p>Comparamos permitir y verificar, respetando límites de seguridad.</p>
    <form onSubmit={submit}><fieldset disabled={loading}>
      <div className="grupo-input"><label className="etiqueta" htmlFor="profile_key">Perfil con historial</label>
        <select className="campo-texto" id="profile_key" value={profileKey} required onChange={event => setProfileKey(event.target.value)}>
          <option value="" disabled>Selecciona un perfil</option>
          {profiles.map(profile => <option key={profile.key} value={profile.key}>{profile.label}</option>)}
        </select>
        {selected && <div className="perfil-resumen"><strong>{selected.resolved_verifications} verificaciones resueltas · {selected.reported_abandons} abandonos</strong><span>{selected.description}</span></div>}
      </div>
      <div className="grupo-input"><label className="etiqueta" htmlFor="merchant">Nombre del comercio</label><input className="campo-texto" id="merchant" name="merchant" defaultValue={initial?.merchant ?? 'Farmacias Demo'} required maxLength={200} /></div>
      <div className="grupo-input"><label className="etiqueta" htmlFor="amount">Importe (unidades monetarias)</label><input className="campo-texto" id="amount" name="amount" type="number" step="0.01" min="0.01" max="1000000" required defaultValue={initial?.amount} /></div>
      <button className="btn-comprar" type="submit" disabled={!profiles.length}>{loading ? 'Evaluando…' : 'Obtener recomendación'}</button>
    </fieldset></form>
    {error && <p role="alert">{error} Consulta el historial antes de repetir si la respuesta se interrumpió.</p>}
    <p>Los perfiles y sus historiales iniciales son escenarios controlados; no representan clientes reales ni fraude confirmado.</p>
  </div>;
}
