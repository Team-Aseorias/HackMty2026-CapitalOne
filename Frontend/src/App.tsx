import { useState, useEffect } from 'react';
import SimuladorCompra from './components/SimuladorCompra';
import FeedReciente from './components/FeedReciente';
import DecisionPanel from './components/DecisionPanel';
import EvaluationDashboard from './components/EvaluationDashboard';
import './app.css';

type Screen = 'simulador' | 'feed' | 'decision' | 'evaluation';

function App() {
  const [vistaActiva, setVistaActiva] = useState<Screen>('simulador');
  const [desplazamientoY, setDesplazamientoY] = useState(0);

  useEffect(() => {
    const rastrearMouse = (e: MouseEvent) => {
      const centroPantalla = window.innerHeight / 2;
      const distancia = e.clientY - centroPantalla;
      setDesplazamientoY(distancia * 0.3);
    };
    window.addEventListener('mousemove', rastrearMouse);
    return () => window.removeEventListener('mousemove', rastrearMouse);
  }, []);

  if (vistaActiva === 'evaluation') {
    return <EvaluationDashboard onBack={() => setVistaActiva('simulador')} />;
  }

  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#ffffff', 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center', 
      padding: '50px 20px',
    }}>
      
      <div style={{ 
        display: 'flex', 
        flexDirection: 'row', 
        alignItems: 'center', 
        justifyContent: 'center', 
        gap: '60px',
        width: '100%',
        maxWidth: '1200px'
      }}>
        
        {/* ZONA DE CONTENIDO: Se expandirá cuando el logo desaparezca */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', width: '100%' }}>
          
          {vistaActiva === 'simulador' && (
            <SimuladorCompra onComprar={() => setVistaActiva('decision')} />
          )}

          {vistaActiva === 'decision' && (
            <DecisionPanel onViewEvaluation={() => setVistaActiva('evaluation')} />
          )}

          {vistaActiva === 'feed' && (
            <>
              <FeedReciente />
              <button 
                onClick={() => setVistaActiva('simulador')}
                style={{
                  marginTop: '20px',
                  padding: '12px 24px',
                  backgroundColor: '#000000',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                  fontSize: '16px'
                }}
              >
                ← Volver al Simulador
              </button>
            </>
          )}

        </div>

        {/* ZONA DERECHA Y TRIÁNGULO: Se ocultan completamente al entrar a 'decision' */}
        {vistaActiva !== 'decision' && (
          <>
            <div style={{ 
              transform: `translateY(${desplazamientoY}px)`, 
              transition: 'transform 0.1s ease-out' 
            }}>
              <div className="triangulo-animado">
                <div style={{ width: 0, height: 0, borderTop: '25px solid transparent', borderBottom: '25px solid transparent', borderRight: '40px solid #e11d48' }}></div>
              </div>
            </div>
            
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
              <h1 style={{ fontSize: '100px', fontWeight: 'bold', color: '#000000', margin: 0, lineHeight: '1' }}>
                ANCLA
              </h1>
              <p style={{ color: '#000000', marginTop: '20px', fontSize: '28px', maxWidth: '450px' }}>
                Motor de decisión de fricción anti-fraude
              </p>
            </div>
          </>
        )}

      </div>

    </div>
  );
}

export default App;