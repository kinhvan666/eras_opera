# financials

<!-- Part of ErasOpera -->

## Scope

Financials covers the money side of the OPERA Cloud data pipeline: **cashiering (folios/postings),
accounts receivable, and back-office operations**. It owns extraction of these entities and their
staging into the warehouse to feed facts such as `fct_folio_transaction` and `fct_ar_transaction`.

## Key Source Files

Application code does not exist yet (greenfield). Authoritative source schemas in `docs/`:

- `docs/OPERA Cloud Cashiering API (26.2.0.0).json` — folios, postings, payments
- `docs/OPERA Cloud Cashiering Asynchronous API (26.2.0.0).json` — bulk cashiering pulls
- `docs/OPERA Cloud Accounts Receivables API (26.2.0.0).json` — AR accounts, invoices, aging
- `docs/OPERA Cloud Back Office Operations API (26.2.0.0).json` — back-office/export financial ops

## Related Context

- `process/context/database/all-database.md` — dimensional model, financial fact grains, conformed dims
- `process/context/tests/all-tests.md` — pytest + dbt test commands
- `process/context/all-context.md` — stack and repository overview

## Current Status

Status: not-started

## Folder Contents

```
process/features/financials/
  active/       -- in-progress plans (each task in a {slug}_{date}/ task folder)
  completed/    -- archived completed plans
  backlog/      -- deferred/future plans
```

All artifacts colocate inside each `{slug}_{date}/` task folder. Do NOT create `reports/` or
`references/` sibling dirs.
