"""Read-only Azure subscription and regional checks; never creates resources."""

import json
import subprocess


def azure(*args):
    result = subprocess.run(["az", *args, "-o", "json"], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def contains_sku(value, name):
    if isinstance(value, dict):
        return value.get("name") == name or any(contains_sku(v, name) for v in value.values())
    if isinstance(value, list):
        return any(contains_sku(v, name) for v in value)
    return False


def main():
    subscription = azure("rest", "--method", "get", "--url",
                         "/subscriptions/{subscriptionId}?api-version=2022-12-01")
    policies = subscription["subscriptionPolicies"]
    print(f"Subscription state: {subscription['state']}")
    print(f"Offer: {policies['quotaId']}; spending limit: {policies['spendingLimit']}")
    if subscription["state"] != "Enabled" or policies["spendingLimit"] != "On":
        raise SystemExit("BLOCKED: restore an Enabled subscription with spending limit On first.")
    if not policies["quotaId"].startswith("FreeTrial_"):
        raise SystemExit("BLOCKED: expected the approved Free Trial offer.")
    locations = azure("appservice", "list-locations", "--sku", "B1", "--linux-workers-enabled")
    if not any(item["name"] == "West US 2" for item in locations):
        raise SystemExit("BLOCKED: Linux B1 not listed in West US 2.")
    capabilities = azure("postgres", "flexible-server", "list-skus", "--location", "westus2")
    if not contains_sku(capabilities, "Standard_B1ms"):
        raise SystemExit("BLOCKED: PostgreSQL B1ms not listed in West US 2.")
    print("Regional SKUs are listed. This is not a capacity reservation.")
    print("Before creation: verify usable credit and exact trial expiry in the portal;")
    print("review the current creation-page estimate against the $35 allowance.")


if __name__ == "__main__":
    main()
