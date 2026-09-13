import { useState } from 'react';
import SimuladorCompra from './Components/SimuladorCompra';
import FeedReciente from './Components/FeedReciente';
import DecisionPanel from './Components/DecisionPanel';
import EvaluationDashboard from './Components/EvaluationDashboard';
import type { DecisionRecord } from './services/api';
import anclaLogo from './assets/ANCLA.png';
import './App.css';
type Screen = 'simulador' | 'feed' | 'decision' | 'evaluation';
export default function App() {
  const [screen, setScreen] = useState<Screen>('simulador');
  const [decision, setDecision] = useState<DecisionRecord | null>(null);
  const select = (record: DecisionRecord) => { setDecision(record); setScreen('decision'); };
  const back = () => setScreen(decision ? 'decision' : 'simulador');
  if (screen === 'evaluation') return <EvaluationDashboard onBack={back} />;
  if (screen === 'feed') return <FeedReciente onBack={back} onSelect={select} />;
  if (screen === 'decision' && decision) return <DecisionPanel key={decision.id} decision={decision} onUpdate={setDecision} onNew={() => setScreen('simulador')} onViewEvaluation={() => setScreen('evaluation')} onViewFeed={() => setScreen('feed')} />;
  return <div className="app-shell"><div className="app-layout">
    <div className="app-content-zone"><SimuladorCompra onComprar={select} initial={decision ?? undefined} />
      <nav className="ancla-actions"><button onClick={() => setScreen('feed')}>Historial</button><button onClick={() => setScreen('evaluation')}>Comparar políticas</button></nav>
    </div><div className="ancla-brand-wrap"><img src={anclaLogo} alt="ANCLA" style={{ maxWidth: '100%', width: 400 }} /><p>Menor costo esperado, con límites de seguridad.</p></div>
  </div></div>;
}
