import { cost, percent } from './api';

export function safetyExplanation(check: { code: string; observed: number; threshold: number }) {
  switch (check.code) {
    case 'risk_limit': return 'Riesgo estimado ' + percent(check.observed) + ' ≥ límite ' + percent(check.threshold) + '.';
    case 'loss_limit': return 'Riesgo × importe = ' + cost(check.observed) + ', por encima o igual al límite de ' + cost(check.threshold) + '. Este cálculo usa el predictor de riesgo, distinto del modelo de costos.';
    case 'amount_limit': return 'Importe ' + cost(check.observed) + ' ≥ límite ' + cost(check.threshold) + '.';
    case 'missing_context': return 'No hay contexto de cuenta ni historial de compras utilizable.';
    case 'attempt_velocity': return check.observed + ' intentos en la ventana reciente, incluido el actual; límite ' + check.threshold + '.';
    case 'verify_abandon_velocity': return check.observed + ' abandonos de verificaciones reportados en la ventana reciente; límite ' + check.threshold + '.';
    case 'amount_outside_training': return 'Importe fuera del rango de entrenamiento: verificar por precaución; las estimaciones no están validadas para este importe.';
    default: return 'Se activó la regla ' + check.code + '.';
  }
}

export function probability(value: number | null) {
  if (value == null) return 'No disponible';
  if (value >= .9995) return '≥99.9%';
  if (value <= .0005) return '≤0.1%';
  return percent(value);
}
