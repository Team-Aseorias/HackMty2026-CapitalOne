import { useState, useEffect } from 'react';
import { obtenerDecisionesRecientes, type DecisionRecord } from '../services/api';
import './FeedReciente.css';

interface FeedProps {
  onBack?: () => void;
}

export default function FeedReciente({ onBack }: FeedProps) {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDecisions = async () => {
      try {
        const data = await obtenerDecisionesRecientes();
        setDecisions(data);
      } catch (error) {
        console.error("Error al obtener el feed", error);
      } finally {
        setLoading(false);
      }
    };

    fetchDecisions();
    const interval = setInterval(fetchDecisions, 5000);
    return () => clearInterval(interval);
  }, []);

  const renderBadge = (action: string, status: string) => {
    if (action === 'allow') return <div className="feed-badge badge-allow">Permitida</div>;
    if (action === 'verify' && status === 'SUCCESS') return <div className="feed-badge badge-verify-success">Exitosa</div>;
    if (action === 'verify' && status === 'ABANDONED') return <div className="feed-badge badge-verify-abandoned">Abandonada</div>;
    return <div className="feed-badge">Pendiente</div>;
  };

  return (
    <main className="feed-page">
      <header className="feed-header">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
          <h1 style={{ fontSize: '50px', fontWeight: 'bold', color: '#000000', margin: 0, lineHeight: '1' }}>
            ANCLA
          </h1>
          <p style={{ color: '#000000', marginTop: '8px', fontSize: '16px', maxWidth: '450px', margin: '8px 0 0 0', fontWeight: 600 }}>
            Historial Operativo (Feed en vivo)
          </p>
        </div>
        
        {onBack && (
          <button type="button" className="back-button" onClick={onBack}>
            ← Volver al panel de decisión
          </button>
        )}
      </header>
      
      {loading && decisions.length === 0 ? (
        <p style={{ textAlign: 'center', fontWeight: '900', fontSize: '18px' }}>Cargando transacciones...</p>
      ) : (
        <ul className="feed-lista">
          {decisions.map((decision) => (
            <li key={decision.id} className="feed-item">
              <div className="feed-item-info">
                <strong>{decision.merchant} - ${decision.amount}</strong>
                <span>ID: {decision.id} • {decision.timestamp}</span>
              </div>
              <div>
                {renderBadge(decision.action, decision.status)}
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}