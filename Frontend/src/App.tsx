import { useEffect, useState } from 'react';
import SimuladorCompra from './Components/SimuladorCompra';
import FeedReciente from './Components/FeedReciente';
import DecisionPanel from './Components/DecisionPanel';
import EvaluationDashboard from './Components/EvaluationDashboard';
import anclaLogo from './assets/ANCLA.png';
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

        {/* Zona Derecha: Logo Animado */}
        <div
          className="ancla-brand-wrap"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            transform: `translateY(${desplazamientoY}px)`,
          }}
        >
            {/* Animación sutil de entrada para la imagen */}
            <div className="ancla-copy-intro">
               <img 
                 src={anclaLogo} 
                 alt="Logo ANCLA" 
                 style={{ 
                   maxWidth: '400px', 
                   width: '100%', 
                   height: 'auto',
                   objectFit: 'contain'
                 }} 
               />
            </div>
            <div className="ancla-copy ancla-copy-intro" style={{ marginTop: '20px', textAlign: 'center' }}>
              <p>Motor de decisión de fricción anti-fraude</p>
            </div>
        </div>

      </div>
    </div>
  );
}
