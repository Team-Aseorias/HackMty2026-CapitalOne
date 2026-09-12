import { useState } from 'react'
import DecisionPanel from './Components/DecisionPanel'
import EvaluationDashboard from './Components/EvaluationDashboard'

type Screen = 'decision' | 'evaluation'

function App() {
  const [screen, setScreen] = useState<Screen>('decision')

  if (screen === 'evaluation') {
    return <EvaluationDashboard onBack={() => setScreen('decision')} />
  }

  return <DecisionPanel onViewEvaluation={() => setScreen('evaluation')} />
}

export default App
