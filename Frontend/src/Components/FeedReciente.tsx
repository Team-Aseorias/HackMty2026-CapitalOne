import { useState, useEffect } from 'react';
import { obtenerDecisionesRecientes, type DecisionRecord } from '../services/api';
import './FeedReciente.css';

export default function FeedReciente() {
  const [decisions, setDecisions] = useState<DecisionRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Función que pide los datos al cargar la página
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
    
    // Opcional: Esto hace que se actualice solo cada 5 segundos (Tiempo real)
    const interval = setInterval(fetchDecisions, 5000);
    return () => clearInterval(interval);
  }, []);

  // Función para determinar cómo se ve la etiqueta según la decisión y el estado
  const renderBadge = (action: string, status: string) => {
    if (action === 'allow') {
      return <div className="feed-badge badge-allow">Permitida Automáticamente</div>;
    }
    if (action === 'verify' && status === 'SUCCESS') {
      return <div className="feed-badge badge-verify-success">Verificación Exitosa</div>;
    }
    if (action === 'verify' && status === 'ABANDONED') {
      return <div className="feed-badge badge-verify-abandoned">Verificación Abandonada</div>;
    }
    return <div className="feed-badge">Pendiente</div>;
  };

  return (
    <div className="feed-container">
      <h2 className="feed-titulo">Historial Operativo (Feed)</h2>
      
      {loading && decisions.length === 0 ? (
        <p style={{ textAlign: 'center', fontWeight: 'bold' }}>Cargando transacciones...</p>
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
    </div>
  );
}