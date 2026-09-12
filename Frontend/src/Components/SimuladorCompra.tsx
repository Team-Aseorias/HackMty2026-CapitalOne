import { useRef, useState, type FormEvent } from 'react';
import { evaluarCompra, type DecisionRecord, type PurchaseAttempt } from '../services/api';
import './SimuladorCompra.css';
export default function SimuladorCompra({ onComprar, initial }: { onComprar: (record: DecisionRecord) => void; initial?: PurchaseAttempt }) {
  const [loading, setLoading] = useState(false);
  const busy = useRef(false);
  const [error, setError] = useState('');
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy.current) return;
    const data = new FormData(event.currentTarget);
    const attempt: PurchaseAttempt = { customer_id: String(data.get('customer_id')).trim(), account_id: String(data.get('account_id')).trim(), merchant: String(data.get('merchant')).trim(), merchant_id: String(data.get('merchant_id')).trim() || undefined, amount: Number(data.get('amount')) };
    busy.current = true; setLoading(true); setError('');
    try { const decision = await evaluarCompra(attempt); onComprar({ ...attempt, ...decision, action: decision.decision, outcome: 'pending', created_at: new Date().toISOString() }); }
    catch (err) { setError(err instanceof Error ? err.message : 'No se pudo evaluar.'); }
    finally { busy.current = false; setLoading(false); }
  }
  return <div className="simulador-card"><h2 className="simulador-titulo">Evaluar una compra</h2>
    <p>Comparamos permitir y verificar, respetando límites de seguridad.</p>
    <form onSubmit={submit}><fieldset disabled={loading}>
      {(['customer_id', 'account_id', 'merchant', 'merchant_id'] as const).map(name => <div className="grupo-input" key={name}>
        <label className="etiqueta" htmlFor={name}>{{ customer_id: 'ID del cliente', account_id: 'ID de la cuenta', merchant: 'Nombre del comercio', merchant_id: 'ID del comercio en Nessie (opcional)' }[name]}</label>
        <input className="campo-texto" id={name} name={name} defaultValue={initial?.[name] ?? ''} required={name !== 'merchant_id'} maxLength={name === 'merchant' ? 200 : 100} pattern={name === 'customer_id' || name === 'account_id' ? '[a-zA-Z0-9_-]+' : undefined} />
      </div>)}
      <div className="grupo-input"><label className="etiqueta" htmlFor="amount">Importe (unidades monetarias)</label><input className="campo-texto" id="amount" name="amount" type="number" step="0.01" min="0.01" max="1000000" required defaultValue={initial?.amount} /></div>
      <button className="btn-comprar" type="submit">{loading ? 'Evaluando…' : 'Obtener recomendación'}</button>
    </fieldset></form>
    {error && <p role="alert">{error} Consulta el historial antes de repetir si la respuesta se interrumpió.</p>}
    <p>La evaluación no cobra ni verifica la compra. Usa identificadores de una cuenta demo autorizada.</p>
  </div>;
}
