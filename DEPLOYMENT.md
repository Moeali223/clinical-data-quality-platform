# Azure deployment and restoration runbook

## Verified status on October 4, 2026

**Not deployed.** No live URL or managed database exists for this project.
Azure reports `Azure subscription 1` as **Warned**, offer
`FreeTrial_2014-09-01`, spending limit **On**. The administrative activity log
contains `Microsoft.Subscription/cancel/action` with status `Succeeded`.
A resource inventory returned no resources at the time checked.

Linux B1 App Service is listed in West US 2. PostgreSQL's West US 2 capabilities
include `Standard_B1ms` (1 vCore, 2 GiB). Listings are not capacity reservations;
per-subscription creation eligibility remains unverified while canceled.
The previously reported $200 remaining/30-day credit is **not independently
verified as currently usable**. No trial-credit API response established a
usable balance. No resource was created and the spending limit was not changed.

## Restore the subscription first

1. Open Azure portal → Subscriptions → **Azure subscription 1** → Overview.
2. Look for **Reactivate**. If cancellation can be reversed without changing the
   Free Trial offer or disabling its spending limit, restore it there.
3. If Reactivate is absent, or the flow requires upgrading to pay-as-you-go,
   stop. Open a billing/subscription support request through **Help + support**.
   Explain: “My Free Trial was canceled. Please restore it if possible with the
   existing trial credit and expiration, preserving the spending limit. I do not
   authorize conversion to pay-as-you-go.”
4. Verify the subscription becomes **Active/Enabled**, the original Free Trial
   offer remains, and spending limit is **On**. Check usable remaining credit and
   the exact expiration date in Cost Management + Billing.
5. Run `az account list --all -o table` and `python3 scripts/azure_preflight.py`.
   The script is read-only and deliberately fails for Warned/Disabled states.

Do not select **Upgrade** or **Remove spending limit**. Trial reinstatement is
subject to Microsoft's decision; it cannot be guaranteed. If restoration is
unavailable under these constraints, use the complete local/Docker demonstration.

References: [subscription states](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-states)
and [reactivation guidance](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-disabled).

## Deployment prerequisites after restoration

The steps below are prepared, not cloud-tested. Before executing creation:

- Re-run the read-only preflight; confirm usable trial credit and expiry in portal.
- Review current rates and creation-page estimates against AZURE_COST_ESTIMATE.md:
  $28.16 base for 30 days, $35 allowance, not a hard resource-spending cap.
- Confirm PostgreSQL 17, B1ms, 32 GB Premium SSD, no HA, seven-day local backups,
  and Linux B1 are available for this subscription in West US 2.
- Use one dedicated resource group. Keep spending limit on throughout.
- Install Azure CLI, PostgreSQL client, and the project's `.venv` dependencies.
- Run the complete tests and `python3 scripts/package_deployment.py`.

No registry, paid monitoring, paid certificate, or additional service is needed.
Budget alerts alone do not enforce a spending cap; the subscription limit is
separate. The API uses Azure's default HTTPS hostname.

## Create the small target (only after all gates pass)

Use Bash for these examples. Choose globally unique server/app names. Example
values below are placeholders, not existing cloud resources:

```bash
export RESOURCE_GROUP=clinical-data-quality-demo
export LOCATION=westus2
export WEBAPP_NAME=replace-with-unique-app-name
export PG_SERVER=replace-with-unique-postgres-name
export PG_ADMIN=clinicaladmin
export PG_DATABASE=clinical_data_quality
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"
az appservice plan create --name clinical-data-quality-plan --resource-group "$RESOURCE_GROUP" --location "$LOCATION" --sku B1 --is-linux
read -r -s -p 'New PostgreSQL admin password: ' PG_PASSWORD
export PG_PASSWORD
az postgres flexible-server create --resource-group "$RESOURCE_GROUP" --name "$PG_SERVER" --location "$LOCATION" --tier Burstable --sku-name Standard_B1ms --storage-size 32 --storage-type Premium_LRS --version 17 --zonal-resiliency Disabled --geo-redundant-backup Disabled --storage-auto-grow Disabled --backup-retention 7 --admin-user "$PG_ADMIN" --admin-password "$PG_PASSWORD" --public-access None
az postgres flexible-server db create --resource-group "$RESOURCE_GROUP" --server-name "$PG_SERVER" --database-name "$PG_DATABASE"
az webapp create --resource-group "$RESOURCE_GROUP" --plan clinical-data-quality-plan --name "$WEBAPP_NAME" --runtime 'PYTHON:3.12'
az webapp update --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --https-only true
az webapp config set --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --startup-file 'python -m uvicorn clinical_data_quality.api:app --host 0.0.0.0 --port 8000'
```

Recheck exact CLI flag support with `az postgres flexible-server create --help`
when deploying; stop if the offered SKU/storage or cost differs from this plan.
Do not substitute a larger SKU automatically. Do not put a literal password in
shell history. Resource creation can take minutes; check progress before retries.

## Networking and schema

Obtain the app's possible outbound addresses:

```bash
az webapp show --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --query possibleOutboundIpAddresses -o tsv
```

Create one PostgreSQL firewall rule per displayed IP, using the same address as
start and end. Temporarily allow your setup machine's public IP too:

```bash
az postgres flexible-server firewall-rule create --resource-group "$RESOURCE_GROUP" --name "$PG_SERVER" --rule-name setup-client --start-ip-address YOUR_PUBLIC_IP --end-ip-address YOUR_PUBLIC_IP
```

Never use `0.0.0.0` “allow all Azure services” or an Internet-wide IP range.
Connect with TLS using `sslmode=require`. Construct connection URLs in Python
with URL-encoded credentials, not by concatenating a password into a shell line.
Initialize `sql/schema.sql` using the existing `initialize_schema` function and
an admin connection. Create a separate application role with SELECT, INSERT,
UPDATE on these tables and USAGE/SELECT on their sequences; give it database
CONNECT and schema USAGE, not schema creation or subscription permissions.
Use that role in the API's `DATABASE_URL`. Keep its password separate from the
admin password. The existing connection functions work with libpq connection
strings too, which avoid URL encoding if you prefer Psycopg `make_conninfo`.

## Settings and ZIP deployment

Store local secret material only under `.azure-local/` (ignored by Git), with
permissions `700` on the directory and `600` on files. Create an app settings
JSON object with these entries:

```text
DATABASE_URL: TLS connection string for the dedicated application role
INGEST_API_KEY: a long random secret, generated with secrets.token_urlsafe(32)
SCM_DO_BUILD_DURING_DEPLOYMENT: true
```

The values must be strings. Never paste settings output or connection strings
into GitHub or documentation. Apply them without displaying the response:

```bash
az webapp config appsettings set --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --settings @.azure-local/appsettings.json --output none
python3 scripts/package_deployment.py
az webapp deploy --resource-group "$RESOURCE_GROUP" --name "$WEBAPP_NAME" --src-path dist/azure-deployment.zip --type zip
```

The allowlisted ZIP contains runtime source, package metadata, README, and
`requirements.txt`. It excludes environments, secrets, tests, and local data.
App Service build automation installs `requirements.txt`, which installs this
project. The explicit startup command handles the src package layout.
Remove the temporary setup-client firewall rule once initialization is finished.

## Cloud acceptance checks

1. Request `https://APP_NAME.azurewebsites.net/health` and `/docs`; expect 200.
2. Upload only `data/synthetic_encounters.csv` with `X-Ingest-Key`; expect 201.
   First run: 20 total, 10 accepted, 10 rejected, 10 issues.
3. Read the returned run's summary/issues and retrieve ENC001; verify stored date
   and run linkage. Reads are public; uploads without the key must return 401.
4. Upload the same sample again; expect 0 accepted, 20 rejected, with existing-ID
   issues. Verify the original encounter is unchanged.
5. Restart the web app and read the original report again. This proves the app
   and managed database work across connections and process restart.
6. Inspect actual incurred cost and remaining credit; record only public URL,
   counts, and status in documentation. Never claim deployment complete until
   these checks pass. `/health` alone does not verify the database.

Use a header file or a terminal variable for curl's private key, not a literal
key saved in command history. Keep the upload key out of screenshots.

## Cleanup before trial expiry

Record the portal's exact expiration date. Export any wanted synthetic demo
results and save verification screenshots several days before expiry. Review
all resources in the dedicated group:

```bash
az resource list --resource-group "$RESOURCE_GROUP" -o table
```

Stopping the web app does not stop App Service-plan billing; stopped PostgreSQL
can still have storage charges. To end resource usage, deliberately delete the
whole dedicated group after reviewing it and backing up wanted data:

```bash
az group delete --name "$RESOURCE_GROUP"
```

This command is destructive and prompts for confirmation. Do not use it on a
shared group. Wait for deletion and verify `az group exists --name
"$RESOURCE_GROUP"` returns false, then check no related paid resources remain.
No upgrade or spending-limit removal is part of cleanup. Unused trial credit
expires; it does not extend the hosting window. Local `docker compose down`
keeps the local volume; cloud cleanup does not affect that local demonstration.

References: [Python build/startup](https://learn.microsoft.com/en-us/azure/app-service/configure-language-python),
[ZIP deployment](https://learn.microsoft.com/en-us/azure/app-service/deploy-zip),
[PostgreSQL setup](https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/quickstart-create-server),
[App Service costs](https://learn.microsoft.com/en-us/azure/app-service/overview-manage-costs).
