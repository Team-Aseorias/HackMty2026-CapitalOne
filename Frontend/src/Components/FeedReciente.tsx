import { useState, useEffect } from 'react';
import { obtenerDecisionesRecientes, type DecisionRecord } from '../services/api';
import anclaLogo from '../assets/ANCLA.png'; // Importamos el logo
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
          {/* LOGO MÁS GRANDE (height: 85px) */}
          <img 
              src={anclaLogo} 
              alt="Logo ANCLA" 
              style={{ height: '85px', width: 'auto', marginBottom: '8px' }} 
          />
          <p style={{ color: '#000000', fontSize: '16px', maxWidth: '450px', margin: '0', fontWeight: 600 }}>
            Historial Operativo (Feed en vivo)
          </p>
        </div>
        
        {onBack && (
          <button type="button" className="back-button" onClick={onBack}>
            Volver
          </button>
        )}
      </header>
      
      {loading && decisions.length === 0 ? (
        <p style={{ textAlign: 'center', fontWeight: 'bold', fontSize: '18px', marginTop: '40px' }}>Cargando transacciones...</p>
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