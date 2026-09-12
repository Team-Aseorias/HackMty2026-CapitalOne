import './DecisionPanel.css'

type Action = 'allow' | 'verify'

interface DecisionOption {
    action: Action
    expectedCost: number
    fraudLoss: number
    frictionCost: number
    abandonmentCost: number
}

interface Decision {
    id: string
    recommendedAction: Action
    fraudRisk: number
    uncertainty: number
    mainReason: string
    merchant: string
    amount: number
    options: {
        allow: DecisionOption
        verify: DecisionOption
    }
}

interface DecisionPanelProps {
    decision?: Decision
    onViewEvaluation?: () => void
    onViewFeed?: () => void
}

const mockDecision: Decision = {
    id: '418',
    recommendedAction: 'verify',
    fraudRisk: 0.68,
    uncertainty: 0.18,
    merchant: 'Tech Store',
    amount: 860,
    mainReason:
        'La verificación reduce suficientemente la pérdida esperada para compensar el costo adicional de fricción.',
    options: {
        allow: {
            action: 'allow',
            expectedCost: 42.8,
            fraudLoss: 40,
            frictionCost: 0,
            abandonmentCost: 2.8,
        },
        verify: {
            action: 'verify',
            expectedCost: 18.4,
            fraudLoss: 8,
            frictionCost: 6.4,
            abandonmentCost: 4,
        },
    },
}

export default function DecisionPanel({
    decision = mockDecision,
    onViewEvaluation,
    onViewFeed,
}: DecisionPanelProps) {
    const riskPercentage = Math.round(decision.fraudRisk * 100)
    const confidence = Math.round((1 - decision.uncertainty) * 100)

    const recommendedOption = decision.options[decision.recommendedAction]
    const alternativeOption =
        decision.recommendedAction === 'allow'
            ? decision.options.verify
            : decision.options.allow

    const estimatedSaving =
        alternativeOption.expectedCost - recommendedOption.expectedCost

    return (
        <main className="decision-page">
            <header className="decision-header">
                {/* APLICAMOS EL FORMATO DEL LOGO PRINCIPAL */}
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                    <h1 style={{ fontSize: '50px', fontWeight: 'bold', color: '#000000', margin: 0, lineHeight: '1' }}>
                        ANCLA
                    </h1>
                    <p style={{ color: '#000000', marginTop: '8px', fontSize: '16px', maxWidth: '450px', margin: '8px 0 0 0' }}>
                        Motor de decisión de fricción anti-fraude
                    </p>
                </div>

                <div className="decision-id">Decisión #{decision.id}</div>
            </header>

            <section className="purchase-summary">
                <div>
                    <span className="label">Comercio</span>
                    <strong>{decision.merchant}</strong>
                </div>

                <div>
                    <span className="label">Importe</span>
                    <strong>
                        ${decision.amount.toLocaleString('es-MX', {
                            minimumFractionDigits: 2,
                        })}
                    </strong>
                </div>
            </section>

            <section className="recommendation-card">
                <span className="section-label">RECOMENDACIÓN DEL MOTOR</span>

                <div className="recommendation-content">
                    <div>
                        <h1>
                            {decision.recommendedAction === 'verify'
                                ? 'Verificar compra'
                                : 'Permitir compra'}
                        </h1>

                        <p>
                            ANCLA recomienda <strong>{decision.recommendedAction}</strong> para
                            esta operación.
                        </p>
                    </div>

                    <div className={`decision-badge ${decision.recommendedAction}`}>
                        {decision.recommendedAction.toUpperCase()}
                    </div>
                </div>

                <div className="risk-container">
                    <div className="risk-header">
                        <span>Riesgo estimado de fraude</span>
                        <strong>{riskPercentage}%</strong>
                    </div>

                    <div className="risk-track">
                        <div
                            className="risk-fill"
                            style={{ width: `${riskPercentage}%` }}
                        />
                    </div>
                </div>
            </section>

            <section className="comparison-section">
                <div className="comparison-header">
                    <div>
                        <span className="section-label">COMPARACIÓN</span>
                        <h2>¿Permitir o verificar?</h2>
                    </div>

                    {estimatedSaving > 0 && (
                        <div className="saving">
                            <span>Reducción estimada de costo</span>
                            <strong>${estimatedSaving.toFixed(2)}</strong>
                        </div>
                    )}
                </div>

                <div className="options-grid">
                    <DecisionOptionCard
                        option={decision.options.allow}
                        selected={decision.recommendedAction === 'allow'}
                    />

                    <DecisionOptionCard
                        option={decision.options.verify}
                        selected={decision.recommendedAction === 'verify'}
                    />
                </div>
            </section>

            <section className="explanation-card">
                <div className="explanation-icon">i</div>

                <div>
                    <span className="section-label">RAZÓN PRINCIPAL</span>
                    <h3>¿Por qué tomó esta decisión?</h3>
                    <p>{decision.mainReason}</p>
                </div>
            </section>

            <section className="confidence-card">
                <div className="confidence-header">
                    <span>Confianza de la estimación</span>
                    <strong>{confidence}%</strong>
                </div>

                <div className="confidence-track">
                    <div
                        className="confidence-fill"
                        style={{ width: `${confidence}%` }}
                    />
                </div>

                <p>Incertidumbre estimada: {Math.round(decision.uncertainty * 100)}%</p>
            </section>

           <section className="decision-next-step">
                <div>
                    <span className="section-label">SIGUIENTE PASO</span>
                    <h3>¿Cómo se comporta ANCLA frente a otras políticas?</h3>
                    <p>
                        Compara esta estrategia con una regla fija y una política predictiva
                        sobre el conjunto de prueba sintético.
                    </p>
                </div>

                {/* Contenedor para que los botones queden uno al lado del otro */}
                <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
                    {onViewFeed && (
                        <button
                            type="button"
                            className="evaluation-link-button"
                            style={{ backgroundColor: '#000000', color: '#ffffff' }} // Botón en negro para diferenciarlo
                            onClick={onViewFeed}
                        >
                            Ver historial (Feed)
                        </button>
                    )}
                    {onViewEvaluation && (
                        <button
                            type="button"
                            className="evaluation-link-button"
                            onClick={onViewEvaluation}
                        >
                            Ver evaluación de políticas →
                        </button>
                    )}
                </div>
            </section>

            <footer className="demo-warning">
                Evaluación basada en un entorno sintético controlado.
            </footer>
        </main>
    )
}

interface OptionProps {
    option: DecisionOption
    selected: boolean
}

function DecisionOptionCard({ option, selected }: OptionProps) {
    const isAllow = option.action === 'allow'

    return (
        <article className={`option-card ${selected ? 'selected' : ''}`}>
            <div className="option-title">
                <div className="option-name">
                    <span className="option-icon">{isAllow ? '✓' : '?'}</span>
                    <h3>{isAllow ? 'Permitir' : 'Verificar'}</h3>
                </div>

                {selected && <span className="recommended-tag">RECOMENDADO</span>}
            </div>

            <div className="expected-cost">
                <span>Costo esperado</span>
                <strong>${option.expectedCost.toFixed(2)}</strong>
            </div>

            <div className="cost-list">
                <CostRow name="Pérdida por fraude" value={option.fraudLoss} />
                <CostRow name="Costo de fricción" value={option.frictionCost} />
                <CostRow name="Costo de abandono" value={option.abandonmentCost} />
            </div>
        </article>
    )
}

function CostRow({ name, value }: { name: string; value: number }) {
    return (
        <div className="cost-row">
            <span>{name}</span>
            <strong>${value.toFixed(2)}</strong>
        </div>
    )
}
