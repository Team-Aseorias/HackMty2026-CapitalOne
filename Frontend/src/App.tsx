import { useEffect, useState } from 'react';
import SimuladorCompra from './components/SimuladorCompra';
import FeedReciente from './components/FeedReciente';
import DecisionPanel from './components/DecisionPanel';
import EvaluationDashboard from './components/EvaluationDashboard';
import './App.css';

type Screen = 'simulador' | 'feed' | 'decision' | 'evaluation';

export default function App() {
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

  // 1. PANTALLA DE EVALUACIÓN
  if (vistaActiva === 'evaluation') {
    return (
      <div style={{ backgroundColor: '#ffffff', minHeight: '100vh', width: '100%' }}>
        <EvaluationDashboard onBack={() => setVistaActiva('decision')} />
      </div>
    );
  }

  // 2. PANTALLA DEL HISTORIAL (FEED)
  if (vistaActiva === 'feed') {
    return (
      <div style={{ backgroundColor: '#ffffff', minHeight: '100vh', width: '100%' }}>
        <FeedReciente onBack={() => setVistaActiva('decision')} />
      </div>
    );
  }

  // 3. PANTALLA DEL PANEL DE DECISIÓN
  if (vistaActiva === 'decision') {
    return (
      <div style={{ backgroundColor: '#ffffff', minHeight: '100vh', width: '100%' }}>
        <DecisionPanel 
          onViewEvaluation={() => setVistaActiva('evaluation')} 
          onViewFeed={() => setVistaActiva('feed')} 
        />
      </div>
    );
  }

  // 4. PANTALLA PRINCIPAL (SIMULADOR + LOGO ANIMADO)
  return (
    <div className="app-shell">
      <div className="app-layout">
        
        {/* Zona Izquierda: Formulario de compra */}
        <div className="app-content-zone">
          <SimuladorCompra onComprar={() => setVistaActiva('decision')} />
        </div>

        {/* Zona Derecha: Logo y triángulo con animación de entrada */}
        <div className="ancla-brand-wrap">
          <div
            className="ancla-triangle-motion"
            style={{ transform: `translateY(${desplazamientoY}px)` }}
            aria-hidden="true"
          >
            <div className="ancla-triangle-intro">
              <div className="ancla-triangle" />
            </div>
          </div>

          <div className="ancla-copy ancla-copy-intro">
            <h1>ANCLA</h1>
            <p>Motor de decisión de fricción anti-fraude</p>
          </div>
        </div>

      </div>
    </div>
  );
}