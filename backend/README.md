# ANCLA backend

FastAPI service for assessing purchase attempts with risk, causal uplift and configurable fraud/friction costs.

## Run locally

```powershell
cd backend
pip install -e .
uvicorn app.main:app --reload
```

The interactive API documentation is available at `/docs`.

To retain personalized verification outcomes across restarts, copy the Atlas
credentials file to `backend/.env` (it is ignored by Git). The application
loads `MONGODB_URI` automatically; without it, it uses the explicit in-memory
demo fallback.

## Nessie and causal decision flow

Set `NESSIE_API_KEY` to use Capital One Nessie and send `merchant_id` with a
purchase attempt. `POST /purchase-attempts` reads the account and its purchase
history first, builds only pre-decision features, and returns the action with
the lowest estimated cost. `POST /decisions/{id}/complete` is the only action
that creates `POST /data/accounts/{account_id}/purchases` in Nessie.

The causal model is a two-model T-learner: one outcome model for randomized
`allow` examples and one for randomized `verify` examples. Its uplift is
`E[cost | allow, X] - E[cost | verify, X]`; positive values favor verification.
It also estimates completion under each action. Previous verification outcomes
for the account are smoothed into a friction-tolerance feature, so a customer
who repeatedly abandons verification is not treated like a new customer.
The included simulator supplies randomized treatment and keeps potential
outcomes only for held-out synthetic evaluation. If Nessie is unavailable, the
API returns `context_source: "local"` and never implies a remote purchase was
recorded.
