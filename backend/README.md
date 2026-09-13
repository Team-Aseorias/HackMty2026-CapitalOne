# ANCLA backend

See [the sequential validity review](reports/SEQUENTIAL_VALIDITY_REVIEW.md) for
measured repeated-abandonment sensitivity, fresh-seed validation and explicit
limits on what this prototype demonstrates.

Policy `safety-v2` adds account-level activity snapshots. Defaults recommend
verify from the fifth persisted attempt (including the current one) in 600
seconds, or after three reported verification abandonments in that window.
Configure `ACTIVITY_WINDOW_SECONDS`, `MAX_WINDOW_ATTEMPTS` and
`MAX_WINDOW_VERIFY_ABANDONS`. These are demo rules, not calibrated fraud
probabilities or an atomic rate limiter. Mongo fallback only sees in-process
records. Static policy evaluations do not measure these temporal rules.

Decision responses now disclose `safety_checks`, `cost_preferred_action`,
`personalization_evidence`, `recent_activity`, `model_warnings` and
`fraud_status: "unknown"`. Outcomes never establish fraud labels.
Training-range warnings flag extrapolation; range membership does not prove
calibration. Amounts outside the training envelope force a verify recommendation.

Verification-history inputs are capped at inference: `prior_verifications` at
12 and the smoothed abandonment rate to the simulator's nominal interval
`[1/18, 13/18]`. Sparse histories still use the population prior. The raw count,
abandonments and smoothed rate remain in `personalization_evidence`, alongside
`model_prior_verifications`, `model_abandonment_rate` and `capped_fields`.
`capped_to_training_range:*` identifies these adjustments; other out-of-range
features still produce extrapolation warnings. The cap does not prove calibration
or joint training support. It applies to new predictions, including batch calls;
stored decisions retain their original estimates. Earlier audit snapshots predate
this inference change and should be regenerated for numerical comparisons.

FastAPI service for assessing purchase attempts with risk, causal uplift and configurable fraud/friction costs.

ANCLA is a recommendation service. It estimates how verification changes a
user's likelihood of completing a purchase, and returns `allow` or `verify`
subject to independent fraud-risk limits. The consuming application decides
how to act on the recommendation and performs any verification or purchase.
ANCLA does not execute or approve verification challenges.

## Perfiles controlados para la demo

`GET /demo-profiles` devuelve tres alias comparables (`estable`, `mixto` y
`friccion`) sin exponer IDs internos. `POST
/demo-profiles/{key}/purchase-attempts` recibe únicamente comercio e importe.
Todos parten del mismo contexto de compra y difieren en su historial inicial de
verificaciones: 0, 3 o 6 abandonos entre 8 resultados. El backend combina ese
fixture con los resultados que se reporten durante la sesión, por lo que las
siguientes decisiones sí incorporan esos abandonos.

Estos perfiles son escenarios controlados, no clientes de Capital One, datos
bancarios reales ni etiquetas de fraude. `ENABLE_DEMO_PROFILES=false` desactiva
las rutas. En despliegue siguen protegidas por `BACKEND_API_KEY` y el gateway.

## Run locally

```powershell
cd backend
pip install -e .
uvicorn app.main:app --reload
```

The interactive API documentation is available at `/docs`.

To retain personalized verification outcomes across restarts, copy the Atlas
credentials file to `backend/.env` (it is ignored by Git). The application
loads `MONGO_URI` automatically; without it, it uses the explicit in-memory
demo fallback. The legacy names `MONGODB_URI` and `MONGODB_DATABASE` remain
accepted during migration.
When Mongo is available, startup creates indexes and the API stores raw attempts,
decisions and outcomes in their corresponding collections.

Known technical debt: the class-based repository used by the inference API and
the functional repository API retained from the database feature share the
`decisions` collection, but do not yet validate against one canonical document
model. The live inference route writes the interoperability fields `id`,
`attempt_id`, `action` and `created_at`; full schema normalization is deferred
until after the demo.

## Nessie and causal decision flow

Set `NESSIE_API_KEY` to use Capital One Nessie and send `merchant_id` with a
purchase attempt. `POST /purchase-attempts` validates the account, its customer
and the merchant through documented, read-only Nessie routes. Purchase and
decision history comes from ANCLA's Mongo store because the current Nessie
OpenAPI exposes neither purchase listing nor purchase creation.
`POST /decisions/{id}/complete` and `/abandon` record outcomes reported by the
consuming application; ANCLA does not substitute a deposit or withdrawal for a
purchase. These outcomes feed future abandonment estimates.

The conditional-outcome learner fits separate `allow` and `verify` arms on
randomized synthetic observations. Each arm separately learns fraud success
and voluntary abandonment among legitimate transactions. Regularized logistic
models were selected using validation seed 2030; the training set contains
12,000 rows (seed 2026). Uplift is `E[cost | allow, X] - E[cost | verify, X]`;
positive values favor verification. Completion probabilities are conditional
on a legitimate transaction, not approval probabilities.

Previous completed/abandoned `verify` decisions with known outcome timestamps
are smoothed into an abandonment-history proxy. At least three resolved
observations are required for personalization. The learned abandonment
coefficient is constrained nonnegative. Fraud heads exclude verification and
abandonment history entirely. Future, unresolved and undated historical feedback
is excluded. This proxy does not prove why an individual abandoned.
The included simulator supplies randomized treatment and keeps potential
outcomes only for held-out synthetic evaluation. If Nessie is unavailable, the
API returns `context_source: "local"` and never implies a remote purchase was
recorded.

## Reproduce the inference audit

From `backend`, after `pip install -e ".[dev]"`:

```powershell
python -m pytest tests -q -p no:cacheprovider
python -m app.ml.compare_estimators
python -m app.ml.audit_inference
python -m app.ml.causal_refutation
python -m app.ml.demo_inference
```

These commands are offline and print JSON; they do not connect to Mongo or Nessie.
See [the measured results and pitch notes](reports/INFERENCE_VALIDATION.md).
DoWhy is not a runtime dependency. The refutations here use NumPy permutation,
bootstrap, data-subset and random-covariate checks; they are not DoWhy outputs.

## Serving and policy limits

`python -m app.serve` starts exactly one worker using `PORT` (default 8000).
Models warm up at startup; `/ready` reports readiness. `DEMO_MODE=true` permits
an in-memory fallback. In strict mode, Mongo and `BACKEND_API_KEY` are required.
API consumers authenticate with `X-API-Key` when the backend key is configured.
This authenticates the consuming service, not the buyer or a fraud challenge.

The default demo safety gates recommend `verify` when predicted fraud risk is
at least 0.15 **and its expected unverified loss covers the fixed verification
cost**, estimated unverified fraud loss is at least 15 amount units, the
purchase is at least 500 amount units, or usable account context is unavailable.
They can be configured through `MAX_SOFT_RISK`, `MAX_SOFT_EXPECTED_LOSS`,
`MAX_SOFT_AMOUNT` and `VERIFY_COST`. These limits are demo assumptions, not
production calibration.
`FRAUD_COST` is retained only for legacy compatibility; current fraud loss scales
with the purchase amount. No automatic model training from live consumer feedback
is performed: training requires adjudicated fraud labels and valid treatment data.
