---
name: tenant-check
description: Review the current diff, or named files, for multi-tenant isolation risks, meaning any database access that could read or write another tenant's rows. Runs the static check first, then does the semantic review it structurally cannot. Use before committing any change that touches the database.
---

# Tenant-isolation review

The rule: every tenant-owned table is scoped by the tenant column, and feature
code goes through the tenant-scoped client, never around it. One query that
reaches the raw client without the filter is a cross-tenant data leak.

## Step 1: run the static check

```bash
npx bouncer-gates --only scope
```

Resolve every blocking finding first: go through the scoped client, add the
tenant filter, or, if the access is genuinely cross-tenant, mark it with
`// bouncer-gates-ok(scope): <a reason that names why it cannot leak>`.

A green run is **necessary, not sufficient**. Continue to step 2.

## Step 2: review what the static check cannot see

Read the changed database code and reason about each of these:

1. **Interactive transactions.** Inside a transaction callback, the client in
   the callback is usually not the scoped one. Every tenant-owned call in it
   needs an explicit tenant filter. This is where checkout, orders and payments
   do multi-step writes, so a miss here is critical.
2. **Hoisted or built filters.** A `where` object built elsewhere passes the
   static check if it mentions the tenant column. Confirm it uses the *current
   request's* tenant, not a value from user input or another record.
3. **Lookups by id.** An update or delete by `id` alone is only safe if that id
   was fetched in the same request with a tenant filter. If the guard query
   moved or changed, the safety claim is now false.
4. **New models.** A new model with a tenant column must be registered as
   tenant-owned wherever the scoped client and `bouncer-gates.config.json` list
   them. An unregistered model is checked by nothing.
5. **Raw SQL.** The tenant predicate must be present AND parameterised, never
   string-concatenated.
6. **New exception comments.** Read each reason. Reject vague ones like "it's
   fine" or "background job". A good one names why it cannot leak.
7. **Background jobs and webhooks.** They run without a request tenant, so they
   legitimately use the raw client, but must then scope by hand or be genuinely
   platform-wide. Confirm which.

## Step 3: report

Verdict: PASS, or a list of findings as `file:line, the risk, the fix`. Rank
cross-tenant **writes** above reads. Do not restate green static output.
