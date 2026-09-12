import './EvaluationDashboard.css'

type PolicyKey = 'fixed' | 'predictive' | 'causal'

interface PolicyMetric {
    key: PolicyKey
    name: string
    shortName: string
    description: string
    netLoss: number
    realizedFraud: number
    legitimateCompleted: number
    verifications: number
    highlight?: boolean
}

interface EvaluationDashboardProps {
    onBack?: () => void
}

const policies: PolicyMetric[] = [
    {
        key: 'fixed',
        name: 'Regla fija',
        shortName: 'Regla fija',
        description: 'Verifica usando una condición estática de riesgo.',
        netLoss: 31840,
        realizedFraud: 14600,
        legitimateCompleted: 842,
        verifications: 386,
    },
    {
        key: 'predictive',
        name: 'Política predictiva',
        shortName: 'Predictiva',
        description: 'Verifica cuando la probabilidad de fraude supera el umbral.',
        netLoss: 27420,
        realizedFraud: 11900,
        legitimateCompleted: 869,
        verifications: 312,
    },
    {
        key: 'causal',
        name: 'Política causal · ANCLA',
        shortName: 'ANCLA',
        description: 'Verifica solo cuando el beneficio esperado compensa la fricción.',
        netLoss: 21860,
        realizedFraud: 10800,
        legitimateCompleted: 901,
        verifications: 228,
        highlight: true,
    },
]

const operationMetrics = [
    { label: 'Decisiones evaluadas', value: '1,250' },
    { label: 'ALLOW / VERIFY', value: '81.8% / 18.2%' },
    { label: 'Tiempo medio de decisión', value: '184 ms' },
    { label: 'Verificaciones completadas', value: '89.5%' },
]

const formatCurrency = (value: number) =>
    new Intl.NumberFormat('es-MX', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
    }).format(value)

export default function EvaluationDashboard({ onBack }: EvaluationDashboardProps) {
    const causal = policies.find((policy) => policy.key === 'causal')!
    const fixed = policies.find((policy) => policy.key === 'fixed')!
    const predictive = policies.find((policy) => policy.key === 'predictive')!

    const vsFixed = fixed.netLoss - causal.netLoss
    const vsPredictive = predictive.netLoss - causal.netLoss
    const maxLoss = Math.max(...policies.map((policy) => policy.netLoss))

    return (
        <main className="evaluation-page">
            <header className="evaluation-header">
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                    <h1 style={{ fontSize: '50px', fontWeight: 'bold', color: '#000000', margin: 0, lineHeight: '1' }}>
                        ANCLA
                    </h1>
                    <p style={{ color: '#000000', marginTop: '8px', fontSize: '16px', maxWidth: '450px', margin: '8px 0 0 0' }}>
                        Evaluación de políticas · conjunto de prueba separado
                    </p>
                </div>

                {onBack && (
                    <button type="button" className="back-button" onClick={onBack}>
                        ← Volver al panel de decisión
                    </button>
                )}
            </header>

            <section className="evaluation-hero">
                <div>
                    <span className="eyebrow">CIERRE DE LA DEMO</span>
                    <h1>¿Qué política genera menor pérdida neta?</h1>
                    <p>
                        Comparamos una regla fija, una política predictiva y la política causal
                        de ANCLA sobre un conjunto de prueba sintético separado.
                    </p>
                </div>

                <div className="evaluation-pill">Evaluación sintética controlada</div>
            </section>

            <section className="story-card">
                <div className="story-number">01</div>
                <div>
                    <span className="eyebrow">NARRATIVA DE LA PRESENTACIÓN</span>
                    <h2>Mismo riesgo aparente, distinta utilidad de verificar</h2>
                    <p>
                        Una regla fija puede verificar operaciones de más. El modelo predictivo
                        identifica riesgo, pero ANCLA agrega una segunda pregunta: si verificar
                        esa compra concreta reduce suficiente pérdida como para justificar la
                        fricción.
                    </p>
                </div>
            </section>

            <section className="operation-section">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">OPERACIÓN</span>
                        <h2>Qué ocurrió durante la demo</h2>
                    </div>
                    <span className="section-note">Datos mock para integración</span>
                </div>

                <div className="operation-grid">
                    {operationMetrics.map((metric) => (
                        <article className="operation-card" key={metric.label}>
                            <span>{metric.label}</span>
                            <strong>{metric.value}</strong>
                        </article>
                    ))}
                </div>
            </section>

            <section className="evaluation-section">
                <div className="section-heading">
                    <div>
                        <span className="eyebrow">EVALUACIÓN SINTÉTICA</span>
                        <h2>Comparación reproducible de políticas</h2>
                    </div>
                    <span className="section-note">Menor pérdida neta es mejor</span>
                </div>

                <div className="loss-card">
                    <div className="loss-card-header">
                        <div>
                            <span className="metric-label">PÉRDIDA NETA ESTIMADA</span>
                            <h3>Resultado sobre el conjunto de prueba</h3>
                        </div>
                        <div className="best-policy-chip">ANCLA · menor costo</div>
                    </div>

                    <div className="loss-bars">
                        {policies.map((policy) => {
                            const width = (policy.netLoss / maxLoss) * 100

                            return (
                                <div className={`loss-row ${policy.highlight ? 'highlight' : ''}`} key={policy.key}>
                                    <div className="loss-label">
                                        <strong>{policy.shortName}</strong>
                                        <span>{policy.description}</span>
                                    </div>

                                    <div className="loss-visual">
                                        <div className="loss-track">
                                            <div
                                                className={`loss-fill loss-fill-${policy.key}`}
                                                style={{ width: `${width}%` }}
                                            />
                                        </div>
                                        <strong>{formatCurrency(policy.netLoss)}</strong>
                                    </div>
                                </div>
                            )
                        })}
                    </div>
                </div>

                <div className="comparison-summary">
                    <article>
                        <span>Reducción estimada vs. regla fija</span>
                        <strong>{formatCurrency(vsFixed)}</strong>
                        <p>Menor pérdida neta estimada en evaluación sintética.</p>
                    </article>

                    <article>
                        <span>Reducción estimada vs. predictiva</span>
                        <strong>{formatCurrency(vsPredictive)}</strong>
                        <p>La decisión incorpora el costo de fricción, no solo riesgo.</p>
                    </article>

                    <article className="accent-summary">
                        <span>Verificaciones aplicadas por ANCLA</span>
                        <strong>{causal.verifications}</strong>
                        <p>Menos verificaciones que las políticas comparadas en este mock.</p>
                    </article>
                </div>

                <div className="policy-table-wrap">
                    <table className="policy-table">
                        <thead>
                            <tr>
                                <th>Política</th>
                                <th>Pérdida neta</th>
                                <th>Fraude consumado</th>
                                <th>Compras legítimas completadas</th>
                                <th>Verificaciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {policies.map((policy) => (
                                <tr className={policy.highlight ? 'recommended-row' : ''} key={policy.key}>
                                    <td>
                                        <strong>{policy.name}</strong>
                                        {policy.highlight && <span className="row-badge">MEJOR RESULTADO</span>}
                                    </td>
                                    <td>{formatCurrency(policy.netLoss)}</td>
                                    <td>{formatCurrency(policy.realizedFraud)}</td>
                                    <td>{policy.legitimateCompleted}</td>
                                    <td>{policy.verifications}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>

            <section className="conclusion-card">
                <div className="conclusion-mark">✓</div>
                <div>
                    <span className="eyebrow">CONCLUSIÓN DEMOSTRABLE</span>
                    <h2>ANCLA reduce la pérdida neta estimada frente a las políticas comparadas.</h2>
                    <p>
                        Este resultado pertenece a un entorno sintético controlado. No representa
                        métricas reales de una institución financiera ni un contrafactual observado
                        en producción.
                    </p>
                </div>
            </section>

            <footer className="evaluation-footer">
                <span>ANCLA</span>
                <p>Motor de decisión de fricción antifraude · Demo de hackathon</p>
            </footer>
        </main>
    )
}
