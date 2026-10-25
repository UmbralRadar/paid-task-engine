# Paid Task Engine v2

A replacement for the business-idea workflow. It discovers explicit paid requests, stores evidence, and fulfills **confirmed** small research/dataset assignments. n8n schedules the engine and sends Telegram summaries; the Python service on your Droplet owns the task ledger, spending allowance, workers, checks and delivery.

**This is an initial working implementation, not a proven income source or a universal autonomous freelancer.** Public-post discovery and fulfillment are deliberately separated by an assignment boundary. No code can reliably assume a stranger has hired you because they posted a budget. This release does not negotiate with strangers, claim social-media jobs, or collect wallet payments by itself.

## What is implemented

| Component | Actual behavior |
|---|---|
| Scout | Rotates four public-web search lanes: data requests, niche forums, Reddit, public social posts. Searches explicit fixed-price requests, not business ideas. |
| Verifier | Separately researches original request, publication date, filled/solved status, budget, eligibility, scope and missing terms. |
| Gate | Rejects stale/unknown dates, missing original-source evidence, contests, low rewards, private-access tasks, upfront payments, public posting and excessive human effort. |
| Queue | SQLite persistence, duplicate URLs and exact normalized buyer/task fingerprints, idempotent confirmed intake. |
| Worker | Produces public-information research and small datasets: Markdown, JSON, CSV. Up to 30 rows, 8 columns, 12 source pages. |
| QA | Checks schema, row counts, duplicates, provenance and quote limits, then independently researches supporting sources and acceptance criteria. No automatic repair spiral. |
| Delivery | Optional SMTP email or fixed HTTPS webhook profile. Configured recipients/endpoints only; never a destination supplied by a model or web page. |
| Accounting | Logs token/search usage, estimated API cost, conservative local allowances and operator-confirmed payment receipts. No inferred revenue. |
| Notifications | Twice-daily concise Telegram digest; no multi-page business-idea report. |

No local shell execution, coding worker, arbitrary plugin installation, private-page scraping, direct Reddit/X APIs, Facebook-group access, automated negotiations, blockchain signing, Payoneer login, or automatic payment verification is included. Current fulfillment is public research/data, not PDFs/images/apps. Discovery may return zero qualified opportunities. Search indexing is neither comprehensive nor real-time.

## One-time setup on the Droplet

Keep the old workflow until the new one is tested. Disable its schedule afterward; do not delete it first.

1. Unzip this folder onto the Droplet. Docker Engine with the Compose plugin must already be installed. Existing n8n is not replaced.
2. In this folder run:

```bash
cp .env.example .env
python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
nano .env
```

Put your OpenAI API key into `OPENAI_API_KEY`. Put the freshly generated secret into `ENGINE_TOKEN`. No wallet secret is needed. Do not commit `.env` to GitHub.

```bash
chmod 600 .env
docker compose up -d --build
python3 ctl.py health
```

Expected health result: `{"ok": true, "version": "2.0.0"}`. The service binds its host port to `127.0.0.1:8088`, not the public internet.

3. If n8n is in Docker, attach its container to the engine network:

```bash
docker ps --format '{{.Names}}'
```

Identify the existing n8n container, then replace the placeholder below:

```bash
docker network connect paid-task-net YOUR_N8N_CONTAINER_NAME
```

For persistence across n8n container recreation, add this **to the existing n8n Compose file**, preserving its other networks:

```yaml
services:
  n8n:
    networks:
      - default
      - paid-task-net
networks:
  paid-task-net:
    external: true
```

The service is reachable from that container at `http://paid-task-engine:8080`. If n8n runs directly on the host, use `http://127.0.0.1:8088`. If you use n8n Cloud, these internal addresses will not work: expose the service behind your own HTTPS reverse proxy with authentication, then use that URL. Do not expose the plaintext development port publicly.

4. Import `paid-task-engine-n8n.json` into n8n.
5. Create an n8n **Header Auth** credential:
   - Name: `Authorization`
   - Value: `Bearer YOUR_ENGINE_TOKEN`
   - Select it in **Start run** and **Check run**.
6. In **Engine settings**, confirm the service URL. In **Send to Telegram**, select your existing Telegram credential and replace the chat ID with your own chat ID.
7. Execute manually. The workflow starts a run, waits/polls, then sends its result. Publish/activate after a successful test. Schedule: 08:00 and 20:00, America/Mexico_City.

The engine uses GPT-4.1 with Responses API web search and JSON-schema outputs. You can change `model` in config, but check model/tool compatibility and update estimated rates too. No ChatGPT/Claude/Gemini subscription is used by this program.

## Default spending and workload

`config.json` is read on each call. Defaults:

- $0.50 local allowance reserved **before** each model request.
- $2 daily local allowance, $10 lifetime trial allowance.
- One scout search, at most one lead verification, one confirmed job per run.
- Up to four hosted search-tool calls and 6,000 output tokens per model request.
- No automatic API retries; failed/uncertain calls retain their allowance.
- Discovered leads must be <=72 hours old, at least $25, and estimate <=5 human minutes.
- Confirmed tasks can be as small as $5 because negotiation is already complete.
- Each lane with zero qualified leads after six scans pauses for seven days.

**The dollar allowances are conservative local accounting, not a guaranteed OpenAI invoice cap.** The service charges each call against the larger of its reservation and estimated actual usage; a single in-flight request can cost more than its reservation. Rates can change, hosted tool usage can vary, and other applications using the same key are outside this ledger. Check provider usage. Initial estimation assumptions: $2/million input tokens, $8/million output tokens, $0.01/search call; cache discounts are ignored. The estimator is not a billing reconciliation tool.

The $10 trial cap never resets automatically. Once exhausted, inspect outcomes and deliberately change it if warranted. Don't delete the database to reset spending or duplicate protections.

## How the first paid task enters the worker

A public post becomes `terms_needed`, never automatically `approved`. It can be a credible lead without a confirmed assignment. This is the remaining human/adaptor handoff.

A task can enter automatically once an approved buyer/source has a defined order feed or a standing agreement. Its intake adapter calls `POST /tasks` with the engine credential and a structured task object. Only give that credential to trusted operator-controlled adapters; it grants administrative access, not just intake. Buyer-facing forms must validate requests separately and must not expose this token.

For a first confirmed order:

```bash
cp task.example.json my-task.json
nano my-task.json
```

Replace all example text with the actual brief, acceptance criteria, reward, deadline, terms reference and public source URLs. Set `assignment_confirmed` and `ai_allowed` to true **only after those facts have been established**. The example intentionally fails validation until completed. Payment terms should include the agreed payment method, token/network if applicable, timing and receiving details as appropriate. Never include seed phrases, private keys or customer login credentials.

```bash
python3 ctl.py assign my-task.json
python3 ctl.py work
```

`work` starts a run without spending on discovery. Save the returned run ID:

```bash
python3 ctl.py run RUN_ID
python3 ctl.py jobs
python3 ctl.py job JOB_ID
python3 ctl.py download JOB_ID
```

The final command downloads a ZIP containing `report.md`, `data.csv`, `data.json`, and `quality-review.json`. Until delivery is enabled, a completed job remains `ready`. The QA is a separate model pass with fresh search plus deterministic checks; it reduces error but is not proof of factual correctness. Use early jobs to assess real quality before turning on unattended delivery.

## Enable delivery once per buyer

The worker never chooses the recipient. Configure a named profile and put its name into that buyer's confirmed task payload.

### Email delivery

Add SMTP credentials to `.env` (SMTP over TLS, default port 465):

```text
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=465
SMTP_USERNAME=your-account
SMTP_PASSWORD=your-app-password
SMTP_FROM=you@your-domain.example
```

Then configure:

```json
"auto_deliver": true,
"delivery_profiles": {
  "buyer-a": {"type": "email", "recipient": "agreed-recipient@buyer.example"}
}
```

Put `"delivery_profile": "buyer-a"` in confirmed tasks. Restart the service after `.env` changes:

```bash
docker compose up -d --force-recreate
```

The email attaches the actual deliverable files and states AI assistance. No prospecting messages are sent. You must have the buyer's agreement that this address is the delivery destination.

### HTTPS webhook delivery

For a buyer/source with a documented receiving API, configure:

```json
"auto_deliver": true,
"delivery_profiles": {
  "buyer-api": {
    "type": "webhook",
    "url": "https://buyer.example/agreed-delivery-endpoint",
    "token_env": "CLIENT_DELIVERY_TOKEN"
  }
}
```

The request includes `job_id`, `external_id`, `ai_assisted`, and a `files` dictionary containing file text. It supplies `Idempotency-Key: JOB_ID`. This is a generic adapter contract, **not** compatibility with every external platform. Agree the payload with the receiving system. Destinations must be public HTTPS; redirects and private-IP targets are rejected. The connection is pinned to the checked IP while preserving TLS hostname validation.

A 2xx response or SMTP acceptance means `submitted`, **not** accepted work or payment. A network timeout could mean delivery happened; the job becomes `delivery_uncertain`. There is no blind automatic retry. Investigate the receiving system before any manual repair.

Already-`ready` jobs are not automatically sent merely by flipping the flag. New confirmed jobs use the setting during fulfillment. This prevents an accidental backlog blast. To send one reviewed ready job after configuring its profile and enabling delivery, run `python3 ctl.py deliver JOB_ID`.

## Payments

The engine does not access your wallet or Payoneer. It does not verify chain receipts or check balances. For now, record actual receipts using an authenticated operator action:

Create `receipt.json`:

```json
{"job_id":"YOUR_JOB_ID","amount_usd":50,"reference":"unique-bank-receipt-or-chain-transaction-reference"}
```

```bash
python3 ctl.py receipt receipt.json
python3 ctl.py metrics
```

This is explicitly **operator-confirmed**, not independently verified. Duplicate references are rejected. Partial payments are permitted and aggregated. No tax, hosting, foreign exchange or human-time expense is calculated. Do not treat a promised reward or a delivery response as revenue.

## How to improve the edge

1. **Specialize on completed work.** Reuse worker format and acceptance checks. Add a new worker only after a real paid task demonstrates demand. Adding twenty general-purpose agents first increases costs without establishing an advantage.
2. **Use narrow sources.** Edit lane queries toward actual buyers/tasks that passed verification; stop queries returning seller posts or discussions. Search adapters can later use explicitly permitted APIs/RSS rather than lagging search indexes.
3. **Prefer contracted repeat tasks.** A standing assignment plus trusted intake removes most negotiation. A stranger's public request is discovery, not an automated purchase order.
4. **Track cash and intervention.** Keep actual paid amount and human minutes separately; the implemented ledger tracks receipts/API estimates. Time saved must be measured, not guessed by the model.
5. **Reject bad work early.** No contests by default, no speculative trading, no unsupported capabilities, no automatic repair loops, no indefinite agent discussions.

These are engineering advantages to test, not demonstrated superiority over other swarms. There is no reliable evidence that this software will earn money, and no self-improving code loop. Lane cooldown is simple yield control; query tuning remains your job.

## Durable state and failure handling

SQLite and bundles live in the named Docker volume `engine-data`. Back it up before changing the schema. One engine process should own this database; in-process locking prevents overlapping runs, and SQL transactions protect allowance accounting. Don't scale this service to multiple replicas without a database-backed job lease.

Task states: `discovered`, `terms_needed`, `rejected`, `verification_error`, `approved`, `working`, `ready`, `submitted`, `quality_failed`, `execution_error`, `delivery_uncertain`, `expired`, `needs_review`.

Restarting marks interrupted work `needs_review`; it never blindly restarts deliveries. A draft that was created before the QA allowance ran out is saved and can resume QA on the next run without regenerating the work. Source URL inclusion checks are necessary but not proof that the underlying fact is correct.

## Testing and validation

```bash
python3 -m unittest discover -s tests -v
```

The supplied tests use simulated model/API/SMTP responses and temporary databases. They cover intake authorization, deduplication, stale/contest filters, atomic allowances, malformed outputs, dataset checks, CSV injection protection, complete worker/QA/bundle flow, interrupted work, delivery uncertainty, receipt deduplication and private webhook rejection.

No paid OpenAI calls, actual customer deliveries, or real n8n instance execution were performed during creation. n8n JSON and JavaScript are structurally checked; installed-version compatibility and real credentials still require your first test. Docker build depends on your Droplet having registry access.

## API quick reference

All routes require `Authorization: Bearer ENGINE_TOKEN`.

| Route | Purpose |
|---|---|
| GET /health | Health/version |
| POST /run | Start asynchronous cycle; JSON `{ "discover": true }` |
| GET /runs/ID | Poll status and report |
| GET /jobs | Recent jobs and states |
| GET /jobs/ID | Full stored task/evidence/result |
| GET /jobs/ID/bundle | Download QA-passed deliverable ZIP |
| POST /tasks | Enqueue confirmed task, schema in task.example.json |
| POST /jobs/ID/deliver | Explicitly deliver one ready job using its configured profile |
| POST /receipts | Record operator-confirmed payment receipt |
| GET /metrics | Cost estimates, reserved allowance, receipts, states and lanes |

## Sources used for implementation

- OpenAI Responses structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI hosted web search: https://developers.openai.com/api/docs/guides/tools-web-search
- OpenAI pricing (verify current account/model): https://developers.openai.com/api/docs/pricing
- n8n HTTP Request credentials: https://docs.n8n.io/integrations/builtin/credentials/httprequest/
- n8n Telegram messages: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.telegram/message-operations/

An optional future Superteam adapter could use https://superteam.fun/earn/agents/ but is **not included**: this release prioritizes your request to explore outside competitive bounty boards. The generic webhook adapter does not implement Superteam, Reddit or X submission.
