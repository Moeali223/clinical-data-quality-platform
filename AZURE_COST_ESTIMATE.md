# Azure deployment cost estimate

Prepared October 4, 2026. Estimate only; no resources have been created.

## Subscription and assumptions

- Azure Free Trial, not Azure for Students.
- User-reported remaining credit: USD $200, expiring in 30 days.
- Spending limit stays enabled; no subscription upgrade is authorized.
- Proposed region: West US 2. Region capacity and subscription SKU availability
  must be checked before deployment.
- One instance of each service, running for 720 hours (30 days).
- Pay-as-you-go public USD retail rates; no reservations or free allowances assumed.

## Proposed services

| Component | Configuration | Rate | Estimated 30-day cost |
| --- | --- | --- | --- |
| API hosting | App Service, Linux Basic B1, one instance | $0.017/hour | $12.24 |
| Database compute | PostgreSQL Flexible Server, Burstable B1ms, one server | $0.017/hour | $12.24 |
| Database storage | 32 GB, standard Premium SSD storage meter | $0.115/GB-month | $3.68 |
| **Base total** | | | **$28.16** |
| **Planning allowance** | Rounded allowance for small extras, not a guaranteed cap | | **$35.00** |

Storage is provisioned capacity, not the size of the 20-row sample. Storage is
billed on a monthly basis; this estimate conservatively uses one full month.
The 30-day compute convention differs slightly from calculators using 730 hours.
At 730 hours, the base estimate is $28.50.

A $35 allowance would leave approximately $165 of the reported $200 credit if
there is no other subscription usage. Unused trial credit still expires at the
end of the trial: this is a short demonstration window, not several months of
hosting purchased with the remaining credit.

## Scope of the estimate

Use one small Linux App Service plan for the API and one managed PostgreSQL
server with no high-availability standby. The proposed first deployment uses
App Service's built-in Python runtime, avoiding a separately billed container
registry. Docker remains the local reproducible demonstration environment.

No custom domain, paid certificate, Application Insights workspace, container
registry, private endpoint, or additional cloud service is included. Connection
settings, HTTPS, and narrowly scoped database firewall rules are part of the
later deployment preparation, not a reason to add more services now.

Backup storage within the database's included allocation should add no charge;
backup usage beyond that allocation, outbound data transfer beyond allowances,
extra IOPS, logs, taxes, currency differences, and other subscription resources
can change the total. The $35 planning allowance is not a technical spending cap.
Review the actual creation-page estimate before approving deployment. Any
applicable free PostgreSQL allowances may reduce usage charges, but this estimate
does not assume eligibility.

## Cost controls and expiration

Keep the Free Trial spending limit enabled. Do not upgrade to pay-as-you-go or
remove that limit as part of this project. Record the exact trial-expiration date
from the portal and plan cleanup before it. Azure can disable the subscription
when its trial expires even if credit remains.

Stopping the web app does not remove charges for its paid App Service plan.
Database storage can also remain billable while compute is stopped. To end the
demo's ongoing resource charges, review deletion of the project's dedicated
resource group, including its plan and database. Deletion would destroy cloud
records and requires a separate explicit decision; export any wanted demo data
first. No deletion is performed by this document.

## Source and verification

The rates were retrieved from the official Azure Retail Prices API for
`armRegionName = westus2`, `priceType = Consumption`, and service names
`Azure App Service` / `Azure Database for PostgreSQL`. The response had 267 items
and no additional result page. Exact matched product/SKU names:

- `Azure App Service Basic Plan - Linux` / `B1`
- `Azure Database for PostgreSQL Flexible Server Burstable BS Series Compute` / `B1MS`
- `Azure Database for PostgreSQL Flex Server Storage` / `Storage`

Sources:

- [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices)
- [App Service Linux pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/linux/)
- [PostgreSQL Flexible Server pricing](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/)
- [App Service billing behavior](https://learn.microsoft.com/en-us/azure/app-service/overview-manage-costs)
- [Azure subscription expiration](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/subscription-disabled)

## Current deployment status

The subscription is canceled (`Warned`), with spending limit `On`. No Azure
resources were created. Remaining usable credit and its expiration cannot be
verified until the existing trial is restored. See [DEPLOYMENT.md](DEPLOYMENT.md)
for restoration, deployment gates, and cleanup. The $35 figure above is the
previously prepared total planning allowance including extras; no additional
services or larger spending allowance have been authorized.
