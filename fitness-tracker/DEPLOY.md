# Deploying the workout tracker

Two deployments live side by side in this folder — pick one, or try both. The
page itself (`index.html`) is shared; only the backend differs.

| | Azure Static Web Apps | Vercel |
| --- | --- | --- |
| Cost | $0 hosting + pennies of storage | $0 on Hobby (personal use only) |
| Database | Table Storage, **in your own subscription** | Neon Postgres, on **Neon's** free tier |
| Sign-in | GitHub OAuth, built in and free | Shared passcode you set |
| Setup | 4 `az` commands | Connect repo, add integration, set one env var |
| Backend files | `azure-api/` | `api/` |

Neither stores anything the other can see; export/import (in the History tab)
moves your history between them.

---

# Option A — Azure

Cheapest shape that still gives you a real database and a URL you can open from
the gym: **Azure Static Web Apps (Free plan) + Azure Table Storage**.

| Piece | Service | Cost |
| --- | --- | --- |
| Web page + HTTPS + custom domain | Static Web Apps, Free plan | $0 |
| API (`/api/workouts`) | Managed Functions, included in SWA Free | $0 |
| Database | Storage account, Table service | well under $0.05/month at this size |
| Login | SWA built-in GitHub auth | $0 |

The Free plan includes 100 GB/month bandwidth and managed functions. A year of
workouts is a few hundred KB in Table Storage — you are billed for storage
(~$0.045/GB/month) plus a fraction of a cent per 10,000 transactions.

## One-time setup

```bash
# 1. Resource group + storage account (pick your own globally-unique name)
az group create -n fitness-rg -l eastus2
az storage account create -n fitnesstracker$RANDOM -g fitness-rg \
    -l eastus2 --sku Standard_LRS --kind StorageV2

# 2. Grab the connection string
az storage account show-connection-string -n <storage-account-name> -g fitness-rg -o tsv

# 3. Create the Static Web App wired to this repo
az staticwebapp create -n fitness-tracker -g fitness-rg -l eastus2 --sku Free \
    --source https://github.com/shahjaidev/explainers --branch main \
    --app-location /fitness-tracker --api-location /fitness-tracker/azure-api --login-with-github

# 4. Give the API the connection string
az staticwebapp appsettings set -n fitness-tracker \
    --setting-names STORAGE_CONNECTION_STRING="<connection string from step 2>"
```

The `platform.apiRuntime` pin in `staticwebapp.config.json` (node:20) is what makes the
v4 Functions programming model work on managed functions — do not drop it.

Step 3 commits a deploy workflow and the `AZURE_STATIC_WEB_APPS_API_TOKEN`
secret to the repo. `.github/workflows/fitness-tracker.yml` here does the same
job — keep whichever one you end up with, not both.

The `workouts` table is created by the API on first write, so there is no
schema step. Data model: one row per finished workout, `PartitionKey` = your
user id, `RowKey` = inverted timestamp (newest first), `data` = the session JSON.

## Checking the deploy

```bash
curl -s https://<your-app>.azurestaticapps.net/api/health
```

| Response | Meaning |
| --- | --- |
| `{"ok":true,"storage":"reachable"}` | API is live and the connection string works. |
| `{"ok":false,"storage":"unconfigured"}` (503) | `STORAGE_CONNECTION_STRING` app setting is missing — redo step 4. |
| `{"ok":false,"storage":"unreachable","code":403}` (503) | Connection string is present but wrong or the key rotated. |
| HTML login page or 401 | The `/api/health` anonymous route rule did not deploy. |
| 404 | The API did not deploy at all — check `api_location` and the `node:20` runtime pin. |

This route is anonymous on purpose so you can curl it before signing in; it
reports reachability only, never account details or workout data.

## Locking it to you

`staticwebapp.config.json` requires an authenticated user for `/api/*`, and the
API partitions by the user id Azure hands it — a signed-in stranger gets their
own empty history, never yours. To block sign-ups entirely, invite only
yourself under **Role management** and change the API rule to
`"allowedRoles": ["owner"]`.

## Running locally

```bash
npm i -g @azure/static-web-apps-cli azure-functions-core-tools@4
cd fitness-tracker/azure-api && npm install && cd ..
# azure-api/local.settings.json: {"Values":{"STORAGE_CONNECTION_STRING":"UseDevelopmentStorage=true"}}
swa start . --api-location azure-api
```

`swa start` fakes the login at `/.auth/login/github`. Without any of this, the
page still works standalone — open `index.html` and everything saves to
localStorage.

---

# Option B — Vercel

Less setup, because the Marketplace integration provisions the database and
injects its connection string for you. The trade is that the data sits on
Neon's free tier rather than in infrastructure you own, and that there is no
free built-in OAuth, so access is a shared passcode instead of a GitHub login.

1. Import the repo at vercel.com, set **Root Directory** to `fitness-tracker`.
2. **Storage → Marketplace → Neon** and create a database. Vercel sets
   `DATABASE_URL` automatically; there is nothing to copy.
3. Add one environment variable: `APP_PASSCODE`, a long random string.
   Without it the API refuses every request — there is no default and no
   unauthenticated fallback.
4. Deploy. Open the app, click "enter passcode" in the header, paste it once;
   it is remembered in that browser.

The `workouts` table is created on first write. Same check as Azure:

```bash
curl -s https://<your-app>.vercel.app/api/health
# {"ok":true,"storage":"reachable","auth":"passcode"}
# {"ok":false,"auth":"unconfigured"}  -> APP_PASSCODE not set
# {"ok":false,"storage":"unconfigured"} -> Neon integration not connected
```

**Be clear-eyed about the passcode.** It is one shared secret with no rotation,
no lockout, and no per-device revocation: anyone who has it can read and write
your history, and changing it signs out every device. That is a reasonable
trade for a personal gym log and a bad one for anything else. Azure's GitHub
login is genuinely stronger, and free — if that matters more than setup time,
use Option A. Swapping the passcode for real OAuth here is a later change.

## Cheaper/other options considered

- **Cosmos DB serverless** — free tier covers 1000 RU/s + 25 GB, but it is one
  per subscription and overkill for a dozen rows a week.
- **App Service Free (F1) + SQLite** — the F1 instance sleeps and its disk is
  not durable across restarts. Not worth it here.
- **Blob storage static website** — marginally cheaper than SWA Free (which is
  $0), but no free API, no auth, no HTTPS custom domain.

## Tests

`cd fitness-tracker && npm install && npm test` runs both backends against
in-memory stand-ins for their databases — no Azure or Neon account needed.
Covered on each: auth rejection, isolation, newest-first ordering, bad
payloads, upsert without duplication, and idempotent delete.

Note that `fitness-tracker/package.json` exists for the Vercel functions; the
Azure build will `npm install` it too. It is harmless, just a few seconds.
