# ANCLA frontend

Interfaz React conectada a FastAPI mediante un gateway del mismo origen.
Requiere Node.js 24 (o posterior compatible) y el backend en ejecución.

## Desarrollo local

1. Instala con `npm ci`.
2. Copia `.env.example` a `.env` y configura `BACKEND_URL` y la misma
   `BACKEND_API_KEY` del backend. Para un backend demo sin clave, puede quedar vacía.
3. Ejecuta `npm run dev` y abre la URL local que imprime Vite.
4. Introduce cliente, cuenta y comercio de una cuenta demo autorizada.
   El nombre del comercio no sustituye su ID de Nessie.

Vite escucha en 127.0.0.1. Si defines DEMO_ACCESS_PASSWORD, el navegador pedirá
DEMO_ACCESS_USER y esa contraseña. Las variables se leen en el servidor; nunca
uses un prefijo VITE_ para secretos.

## Producción / Render

Este frontend requiere un **Web Service Node**, no un Static Site:
el gateway mantiene la clave del backend fuera del bundle público.

- Root Directory: `Frontend`
- Build Command: `npm ci && npm run build`
- Start Command: `npm start`
- Node: 24
- Variables obligatorias: `BACKEND_URL` (URL HTTPS del backend),
  `BACKEND_API_KEY` (la misma del servicio backend),
  `DEMO_ACCESS_USER` y `DEMO_ACCESS_PASSWORD` (acceso privado a la demo).
- `PORT` lo proporciona Render; localmente usa 3000.

Usa HTTPS en el despliegue. El acceso compartido es para operadores de la demo:
el historial del backend es global, no un portal de compradores con aislamiento
por usuario. No se ha creado ni desplegado un nuevo servicio automáticamente.
El servidor de producción rechaza iniciar sin credenciales.
`npm run preview` utiliza este mismo servidor y requiere esas variables.

## Qué muestra

- Intento real: POST /purchase-attempts, con monto, cliente, cuenta y comercio.
- Recomendación: riesgo, costos esperados, probabilidades de completar **condicionadas
  a una compra legítima**, abandono incremental en puntos porcentuales, seguridad
  y personalización. No inventa confianza ni desglose de costos.
- Outcomes: complete/abandon reportan un desenlace observado; no cobran ni realizan
  verificaciones. Ante una respuesta incierta consulta el historial antes de repetir
  una compra, porque el endpoint de creación no tiene clave de idempotencia.
- Historial: últimas 25 decisiones, refrescadas cada 5 segundos sin peticiones
  superpuestas; permite recuperar una decisión y reportar su resultado.
- Métricas operativas: snapshot al abrir la pantalla, con fuente y pendientes.
- Evaluación: ejecución explícita con semilla y tamaño; muestra las cinco políticas,
  medias por intento, tasas y violaciones. El ganador se calcula entre políticas
  sin violaciones y no se presenta como superioridad estadística.
- Las cantidades están en unidades monetarias: el backend no declara divisa.

Cuando Nessie no está disponible, la interfaz identifica el contexto local.
Cuando se usa memoria, advierte que los registros pueden perderse.
El backend se entrenó con datos sintéticos y no reentrena automáticamente con
los resultados de esta interfaz.

## Validación

```powershell
npm run build
npm run lint
npm test
npm run test:integration
```

Las pruebas del gateway usan un proveedor HTTP local controlado, sin escrituras
a Nessie o Mongo. Para validar inferencia y outcomes reales offline:
`python -m pytest tests/test_inference_http.py tests/test_recommendation_scope.py -q -p no:cacheprovider`
desde backend.

`test:integration` requiere Python con las dependencias del backend. Arranca
FastAPI real en un puerto temporal, deshabilita Mongo/Nessie y recorre las
funciones HTTP del frontend a través del gateway. Todos sus datos son temporales.
