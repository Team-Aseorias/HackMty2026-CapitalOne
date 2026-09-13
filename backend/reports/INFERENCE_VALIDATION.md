# Validación de inferencia ANCLA — synthetic-v3

ANCLA predice la propensión a abandonar ante una verificación y recomienda
`allow` o `verify` dentro de límites de riesgo. No verifica usuarios ni ejecuta
compras. Los endpoints de outcomes reciben retroalimentación del consumidor.

## Evidencia medida

Se comparó la implementación anterior con la nueva sobre los mismos 9,000
intentos sintéticos: 3,000 por semilla 3101, 3102 y 3103. El entrenamiento usa
semilla 2026. La selección de estimador usó otro conjunto, semilla 2030; los
tests adicionales emplean 5201–5203. Las filas del simulador son independientes;
esto no equivale a una validación temporal o por usuario con datos bancarios.

| Métrica promedio entre las tres muestras | Antes | Ahora |
|---|---:|---:|
| Brier de abandono, compradores legítimos asignados a verify | 0.088965 | 0.068035 |
| Brier de fraude, todos los intentos | 0.143082 | 0.139323 |

Un Brier menor indica menor error cuadrático de probabilidad. La reducción es
23.53% para abandono y 2.63% para fraude; no significa 23.53 puntos de accuracy
ni prueba por sí sola una mejor calibración. Los JSON también incluyen curvas
de fiabilidad por intervalos, ECE, log loss, ROC-AUC y precisión-recall.

El ROC-AUC de fraude de la nueva versión fue 0.766, 0.752 y 0.751. El ECE de
abandono fue 0.0156, 0.0169 y 0.0097. En el subgrupo con historial de abandono
alto solo hubo 102 casos observados por muestra: sus métricas son más variables
y necesitan más datos antes de sacar conclusiones sobre ese segmento.

## Cambios que explican la mejora

- Separamos el bloqueo de fraude de un abandono voluntario. Antes se entrenaba
  la probabilidad de completar mezclando ambas situaciones.
- Sustituimos el ajuste de fricción fijo por un coeficiente aprendido con
  restricción de monotonía y regularización. La comparación de validación
  favoreció la regresión logística sobre el bosque calibrado anterior.
- Ampliamos entrenamiento de 2,000 a 12,000 observaciones sintéticas.
- Los modelos de fraude no reciben historial de abandono ni de verificaciones.
- Excluimos datos futuros, feedback pendiente y resultados sin fecha conocida;
  el historial incompleto no se utiliza para personalizar.
- Los modelos solo consumen features anteriores a la decisión y etiquetas
  observadas en su brazo de tratamiento. Los campos contrafactuales del
  simulador se usan exclusivamente para puntuar la evaluación.

Estos cambios se evaluaron juntos. La mejora global no puede atribuirse
exclusivamente a aumentar datos o a cambiar de estimador.

## Comportamiento y límites de riesgo

Sobre 9,000 pares artificiales de la misma transacción y riesgo, cambiar el
historial de 12 verificaciones sin abandonos a 12 con abandonos produjo 352
cambios de `verify` a `allow`, cero cambios en sentido contrario y cero
violaciones de monotonía. Son perfiles extremos para probar comportamiento;
el porcentaje no estima la reducción real de verificaciones en una población.

La política final tuvo cero violaciones de los límites configurados en las
tres muestras. Se compararon regla fija, riesgo predictivo, política causal sin
límites, política causal sin personalización y política causal final.

La personalización redujo ligeramente las verificaciones frente a la versión
sin personalización; en estas muestras no cambió el abandono agregado observado
ni la pérdida por fraude de esa comparación. No hay evidencia aquí para prometer
una reducción grande de abandonos o un aumento de conversión en producción.
Tampoco puede afirmarse que la seguridad esté garantizada: los límites operan
sobre predicciones falibles y deben calibrarse con datos reales.

## Ejemplo reproducible para el pitch

`python -m app.ml.demo_inference` muestra un caso ilustrativo cercano al umbral,
elegido para explicar la decisión; no es un benchmark de rendimiento:

| Perfil | Importe | Riesgo de fraude | Abandono previsto ante verify | Recomendación |
|---|---:|---:|---:|---|
| Sin abandonos en 12 verificaciones previas | 150 | 6.38% | 2.22% | verify |
| Con abandonos en 12 verificaciones previas | 150 | 6.38% | 11.93% | allow |
| Mismo historial sensible, importe por encima del límite | 1,000 | 28.37% | 61.11% | verify |

El importe está expresado en las mismas unidades que los costos configurados.
La recomendación cambia por fricción en el par de riesgo idéntico; el tercer
caso muestra que la propensión al abandono no anula el límite de riesgo.

## Refutaciones y papel de DoWhy

Sobre 4,732 transacciones legítimas del simulador (semilla 4100) y 300
repeticiones, el efecto promedio de verify sobre abandono fue +8.74 puntos
porcentuales, con intervalo bootstrap de 7.62 a 9.93. Al permutar el tratamiento,
el efecto promedio fue -0.006 puntos, cercano a cero. Agregar una covariable
aleatoria produjo 8.741 puntos; usar subconjuntos del 80% dio un intervalo de
8.15 a 9.29 puntos. El p-valor de permutación fue 0.00332.

Estas refutaciones están implementadas con NumPy, no con DoWhy. Verifican que
la tubería reconoce la señal que el propio simulador genera. No validan el
efecto individual ni descartan confusión no observada en una población real.

DoWhy sí aporta valor como capa de evaluación offline: expresar un grafo causal,
identificar el efecto estimable, estimarlo y someterlo a refutaciones. No mejora
automáticamente la precisión del predictor ni convierte asociación en causalidad.
Documentación: [estimación e identificación](https://www.pywhy.org/dowhy/v0.11/user_guide/causal_tasks/estimating_causal_effects/index.html),
[ejemplos de refutación](https://www.pywhy.org/dowhy/v0.11.1/example_notebooks/dowhy_simple_example.html).
Para interpretar Brier y calibración: [documentación de scikit-learn](https://scikit-learn.org/stable/modules/calibration.html).

Un siguiente experimento real requeriría medir abandono voluntario y fraude
confirmado por separado; registrar la probabilidad de asignación de tratamiento;
controlar las variables que determinan la verificación; y verificar que existan
ambos tratamientos en contextos comparables. Una política determinista puede
carecer de ese solapamiento. El diseño debe restringir cualquier exploración al
segmento permitido por el sistema de riesgo del banco.

Frase defendible para el pitch: **“Estimamos qué fricción es evitable para cada
perfil y recomendamos menos verificaciones dentro de límites de riesgo. Probamos
la hipótesis en un simulador aleatorizado y dejamos explícita su validación
pendiente con datos reales.”** No afirmar que se usó DoWhy: no está instalado.

## Artefactos y reproducción

- `inference_baseline.json`: snapshot previo a synthetic-v3.
- `inference_enhanced.json`: resultados medidos de la versión mejorada.
- `model_selection.json`: comparación con semilla de validación independiente.
- `causal_refutation.json`: permutation, bootstrap, subconjuntos y covariable aleatoria.
- `demo_examples.json`: salida de los tres ejemplos ilustrativos.

Desde backend: `python -m pytest tests -q -p no:cacheprovider`,
`python -m app.ml.audit_inference`, `python -m app.ml.causal_refutation` y
`python -m app.ml.demo_inference`. La suite completa pasó 49 pruebas. No se
conectó con Atlas/Nessie ni se ejecutaron verificaciones o compras para esta
validación. Las pruebas HTTP utilizan contextos simulados y la inferencia real.
