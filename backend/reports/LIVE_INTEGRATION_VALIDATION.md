# Validación real de Atlas y Nessie

Resultado: **aprobado para el contrato actual**. ANCLA consulta recursos
documentados de Nessie y persiste intentos, decisiones y outcomes en Atlas.

## Contrato aplicado

El OpenAPI actual de Nessie no ofrece creación ni listado de compras. La
integración usa únicamente:

- `GET /accounts/{id}`
- `GET /accounts/{id}/customer`
- `GET /merchants/{id}`
- `GET /purchase/{purchase_id}` cuando el consumidor ya conoce un ID

ANCLA no representa una compra como depósito o retiro. Los endpoints
`POST /decisions/{id}/complete` y `/abandon` reciben el resultado del sistema
consumidor y lo guardan en Mongo con `outcome_source=consumer_report`.

## Prueba en vivo

Se utilizaron estos recursos demo:

- Cliente: `b25c5e57-ec92-4360-b624-b1e24bcf5615`
- Cuenta: `ee57daa0-ff9b-45f0-b5a6-f33c238eb816`
- Comercio: `8a4a9661-6e3a-4c94-b19d-d4e6511dbeec`

Las tres consultas documentadas respondieron correctamente y la cuenta
pertenece al cliente indicado. El flujo creó dos registros de prueba en ANCLA:

- completed: `8b9edd93-dba8-47f1-905e-cdffda4b8514`
- abandoned: `7f3a3363-9a69-4130-985b-f4a21432788d`

Se comprobó en Atlas la existencia del purchase attempt, la decisión y el
outcome de cada caso. El feed contiene ambos registros y las métricas se leen
de Mongo. Tras limpiar los registros antiguos, una comprobación desde otro
proceso mostró 2 intentos, 1 allow, 1 verify, 1 completed, 1 abandoned y 0
pending. La repetición del mismo resultado fue idempotente y el resultado
contrario devolvió 409. Escrituras a Nessie durante el flujo corregido: cero.

La validación recorrió la aplicación FastAPI y sus modelos reales mediante
ASGI; no representa todavía una prueba contra un despliegue público en Render.

## Pruebas automatizadas

La suite pasó **51 pruebas**. Incluye comprobaciones de que el adaptador:

- genera exactamente las rutas documentadas;
- no expone métodos de listado o creación de compras no documentados;
- no crea transacciones al recibir feedback de completion;
- conserva los límites de riesgo y el comportamiento de inferencia.

## Incidente de la prueba anterior

Antes de recibir la lista definitiva de endpoints se probó la ruta heredada no
documentada `POST /accounts/{id}/purchases`. Nessie aceptó una compra demo de
importe 1 con ID `35306e3c-ccd0-4370-b3e5-79be0e3c90dd`, pero después no pudo
leerla porque su respuesta carece de `status`. Esa ruta fue retirada del código
y ya no forma parte del flujo. La compra demo se eliminó correctamente mediante
el endpoint documentado `DELETE /purchase/{id}`. También se eliminaron de Atlas
los dos attempts, decisions y outcomes de la prueba anterior; se conservaron
los dos casos válidos indicados arriba.

## Reproducción

Desde la raíz, una fase `exercise` crea dos nuevos registros de prueba en Atlas:

```powershell
.venv/Scripts/python.exe backend/scripts/smoke_live.py --phase exercise --merchant-id 8a4a9661-6e3a-4c94-b19d-d4e6511dbeec --customer-id b25c5e57-ec92-4360-b624-b1e24bcf5615 --account-id ee57daa0-ff9b-45f0-b5a6-f33c238eb816
```

La fase `verify`, con los IDs emitidos por `exercise`, comprueba persistencia
desde otro proceso sin generar registros nuevos. Las credenciales se cargan del
entorno y nunca se imprimen.
