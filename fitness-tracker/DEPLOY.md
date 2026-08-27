# Deploying the workout tracker on Azure

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
    --app-location /fitness-tracker --api-location /fitness-tracker/api --login-with-github

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

## Locking it to you

`staticwebapp.config.json` requires an authenticated user for `/api/*`, and the
API partitions by the user id Azure hands it — a signed-in stranger gets their
own empty history, never yours. To block sign-ups entirely, invite only
yourself under **Role management** and change the API rule to
`"allowedRoles": ["owner"]`.

## Running locally

```bash
npm i -g @azure/static-web-apps-cli azure-functions-core-tools@4
cd fitness-tracker/api && npm install && cd ..
# api/local.settings.json: {"Values":{"STORAGE_CONNECTION_STRING":"UseDevelopmentStorage=true"}}
swa start . --api-location api
```

`swa start` fakes the login at `/.auth/login/github`. Without any of this, the
page still works standalone — open `index.html` and everything saves to
localStorage.

## Cheaper/other options considered

- **Cosmos DB serverless** — free tier covers 1000 RU/s + 25 GB, but it is one
  per subscription and overkill for a dozen rows a week.
- **App Service Free (F1) + SQLite** — the F1 instance sleeps and its disk is
  not durable across restarts. Not worth it here.
- **Blob storage static website** — marginally cheaper than SWA Free (which is
  $0), but no free API, no auth, no HTTPS custom domain.

## Tests

`cd fitness-tracker/api && npm install && npm test` runs the handler against an
in-memory stub of Table Storage: auth rejection, per-user isolation, newest-first
ordering, bad payloads, and idempotent delete.
