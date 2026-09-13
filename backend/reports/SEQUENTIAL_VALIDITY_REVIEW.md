# ANCLA — Validez del modelo y abandonos repetidos

## Dictamen

La herramienta demuestra una hipótesis de decisión bajo supuestos sintéticos:
la fricción estimada puede cambiar la acción de menor costo, manteniendo límites
de riesgo independientes. No demuestra que la magnitud de adaptación a una
persona real sea correcta, ni que detecte ataques con una tasa conocida.

La revisión mantuvo los parámetros del modelo y el suavizado. No se aceleró el
incremento de costo para conseguir una demostración visual más llamativa. Se
añadieron diagnósticos, reglas temporales explícitas y pruebas para revelar lo
que el sistema puede y no puede afirmar.

## Por qué el costo de verificar sube lentamente

Para el historial de verificaciones con resultado conocido:

- Durante 0–2 resultados, la tasa histórica de entrada permanece en 1/6.
- Con 3 o más: tasa = (abandonos reportados + 1) / (verificaciones resueltas + 6).
- Con todos abandonados, a los 3 resultados es 44.44%; a los 6, 58.33%;
  a los 12, 72.22%. No pasa directamente a 100%.
- Esa tasa es una **variable de entrada**, no la predicción de abandono.
  La regresión ajustada sobre el simulador también usa importe, comercio,
  contexto y número de verificaciones anteriores.
- Por ello pueden aparecer pequeños cambios antes de tres resultados: el
  número de verificaciones entra en el modelo, aunque su tasa personal aún
  esté reemplazada por el valor de referencia.
- No hay reentrenamiento online: cambian las variables de entrada, no los
  coeficientes del modelo.
- La consulta de personalización utiliza como máximo 50 decisiones resueltas.
  Si las últimas 50 son equivalentes, la adaptación puede estabilizarse.
- Variar historial, importe, hora o comercio simultáneamente impide atribuir un
  cambio exclusivamente a los abandonos.

El costo usa probabilidades separadas:

Cada estimación se refiere a la próxima compra. No es la suma de pérdidas de
todas las compras previas: reportar un abandono de 600 no agrega 600 al costo
de la siguiente evaluación.

```text
costo verificar =
    importe × probabilidad modelada de fraude consumado bajo verify
  + costo fijo de verificar
  + (1 − probabilidad modelada de fraude bajo allow)
    × probabilidad de abandono legítimo bajo verify
    × importe × tasa de costo de abandono
```

La tasa de costo de abandono configurada es 0.15, no el importe completo.
Incluso un incremento de varios puntos porcentuales de abandono puede agregar
solo unas unidades al costo esperado.

## Secuencia controlada de 600

Mismo cliente artificial, mismo comercio conocido, cinco compras previas de
600, misma fecha y hora de evaluación, cuenta abierta en 2025. Se varía solo el
número y la separación temporal de abandonos de verificaciones anteriores.
Estos valores **no son una lectura de la cuenta real del usuario**.

| Abandonos anteriores | Tasa histórica suavizada | Abandono predicho bajo verify | Costo verificar |
|---:|---:|---:|---:|
| 0 | 16.67% | 1.43% | 25.32 |
| 3 | 44.44% | 3.09% | 26.69 |
| 6 | 58.33% | 4.62% | 27.94 |
| 12 | 72.22% | 7.15% | 30.02 |
| 20 | 80.77% | 9.86% | 32.25 |

El caso de 20 ya está fuera del soporte nominal de historial del entrenamiento,
que genera hasta 12 verificaciones previas. Ahora se advierte esa extrapolación.
Estar dentro de los rangos tampoco prueba suficiente cobertura conjunta.

Las 51 variantes entre 0 y 50 no mostraron descensos del costo de verificar
en este perfil. El riesgo permaneció en 9.394% y el costo de permitir en 51.97.
El resultado siempre fue VERIFY: 600 supera el límite de importe de 500.
Esta secuencia sirve para medir sensibilidad, **no para demostrar un cambio a
ALLOW** ni para demostrar calibración individual.

## Qué significa completar, abandonar y fraude

En tráfico real, el resultado de fraude continúa como `unknown`. El endpoint
de resultado solo registra `completed` o `abandoned` y su procedencia como
reporte del consumidor. Ninguno etiqueta una compra como legítima o fraudulenta.

El historial de compras completadas sí contribuye al contexto, por ejemplo a
reconocer un comercio o estimar el importe típico. Esto no equivale a una etiqueta
de legitimidad: ese contexto puede incluir fraude aún desconocido. Es una
limitación para producción y para cualquier afirmación de aprendizaje real.

En el simulador hay etiquetas sintéticas explícitas de fraude, independientes
del resultado de completar. En las nuevas 9,000 observaciones hubo 1,837 casos
de fraude; la política causal con seguridad recomendó ALLOW en 219. Los límites
actúan sobre estimaciones falibles y no eliminan todo fraude.

El valor cercano a 100% de completar bajo ALLOW surge del supuesto del simulador
de que una compra legítima sin verificación no abandona. Es una probabilidad
condicional dentro de ese supuesto, no certeza de legitimidad.
La interfaz ahora evita redondear probabilidades como certeza exacta y explica
ese supuesto junto al dato.

## Frecuencia: brecha encontrada y corrección

Antes de esta revisión, un historial igual de abandonos, repartido en minutos
o días, generaba las mismas predicciones. La personalización filtraba fechas
futuras, pero no medía velocidad. El predictor de fraude excluye explícitamente
la historia de abandono; el historial de compras completadas no suplía esta
señal de intentos repetidos.

Se agregó una instantánea temporal por cuenta sobre decisiones persistidas
de cualquier resultado, incluidas las pendientes:

- Ventana configurable: 600 segundos.
- Desde el quinto intento dentro de la ventana, incluido el actual: VERIFY.
- Con tres abandonos de verificaciones reportados dentro de la ventana:
  VERIFY en el siguiente intento.
- Se usan fechas de recepción generadas por el servidor; cambiar
  `occurred_at` no oculta una ráfaga actual.
- Las resoluciones recientes de intentos antiguos también cuentan para los
  abandonos recientes.
- Registros futuros, sin fecha válida y resultados todavía desconocidos
  no se interpretan como abandonos.
- Historial de otra cuenta no interviene.

Son **reglas de precaución configuradas para la demo**, no un modelo entrenado
de fraude temporal. No aumentan artificialmente el porcentaje de fraude.
Los umbrales requieren validación con tráfico representativo. Pueden añadir
fricción a un cliente legítimo; el coste de ese efecto no está cuantificado
por la evaluación actual de filas independientes.

Límite técnico: la instantánea no es un contador atómico ni un limitador de
solicitudes. Peticiones concurrentes aún no persistidas pueden compartir la
misma cuenta previa. Tampoco cuenta peticiones rechazadas antes de crear una
decisión. No afirmar resistencia completa a ataques automatizados.

## Evaluación nueva: semillas 6201, 6202 y 6203

Modelo y configuración fijos; 3,000 casos por semilla; entrenamiento 2026.
No se reajustaron parámetros con estos resultados.

- ROC-AUC de fraude: 0.7595, 0.7533 y 0.7547.
- Brier medio de fraude: 0.139365.
- Brier medio de abandono legítimo bajo verify: 0.075757.
- ECE de abandono global: 0.0166, 0.0197 y 0.0167.
- En el subgrupo con historial sensible, solo hubo 93, 92 y 90 observaciones.
  Sus ECE fueron 0.0960, 0.0569 y 0.0523: las medias globales ocultan debilidad
  y variabilidad en ese segmento.
- Cero violaciones de los límites estáticos configurados en la política causal.
- En 9,000 pares controlados de historial bajo/alto hubo 353 cambios VERIFY →
  ALLOW, cero cambios inversos y cero violaciones de la prueba de monotonía.
  Son pruebas de comportamiento artificial, no una tasa de mejora comercial.
- Diferencia de costo medio causal − predictivo: −0.17067 u.m. por intento.
  Bootstrap pareado de 1,000 repeticiones (semilla 6204):
  intervalo 95% [−0.36915, −0.000024]. El extremo superior es prácticamente cero;
  no es evidencia robusta de una ventaja grande, ni generaliza a un banco real.
- La personalización no gana en todas las muestras: en semilla 6202 la causal
  personalizada cuesta 15.7845 frente a 15.7474 sin personalización.
- La política causal verifica más que la predictiva en estas tres muestras.

El bootstrap condiciona en un único modelo entrenado y en este simulador. No
incorpora incertidumbre por volver a entrenar, cambios de población o sesgos
del propio simulador. No se usó para seleccionar otro modelo ni ajustar umbrales.

## Qué podemos demostrar y qué falta

**Respaldado:** la integración usa inferencia real; las reglas se cumplen en las
pruebas; la fricción histórica puede modificar una recomendación cuando seguridad
lo permite; los resultados quedan diferenciados de etiquetas de fraude.

**Parcial:** el modelo reconoce señal y obtiene mejores decisiones que algunas
políticas en el simulador. Hay ganancia media pequeña y variabilidad por subgrupo.

**No demostrado:** cuánto debe subir el costo tras cada abandono real; fraude
individual confirmado; mejora de conversión en producción; tasas de detección de
ráfagas; aprendizaje causal válido a partir de los clics de esta demo.

Para validar lo pendiente hacen falta etiquetas de fraude adjudicado separadas
del desenlace, fechas de observación de esas etiquetas, sesiones/cuentas,
asignación y ejecución real de verificación, causas de abandono y un conjunto
temporal separado. La política que verifica siempre a un segmento no proporciona
comparaciones observadas de ALLOW en ese mismo segmento. Los datos sintéticos
aleatorizados permiten esa comparación en el simulador; los reportes de uso no
la garantizan.

## Artefactos y reproducción offline

- `sequence_sensitivity.json`: secuencias de minutos y días, probabilidades,
  costos, reglas activadas y advertencias.
- `validity_fresh_seeds.json`: métricas completas, subgrupos, políticas y
  bootstrap pareado.
- `python -m app.ml.audit_sequences`
- `python -m app.ml.audit_validity`
- `python -m pytest tests -q -p no:cacheprovider`
- Desde Frontend: `npm run build`, `npm run lint`, `npm test`,
  `npm run test:integration`.

Ninguna auditoría accede a Mongo o Nessie. Los tests HTTP usan almacenamiento
aislado en memoria. No se cambiaron datos externos ni configuración de despliegue.
