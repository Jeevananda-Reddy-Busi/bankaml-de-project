# Bank AML Data Engineering Platform — Setup & Execution Guide

This guide explains how a new engineer can configure the project, deploy the Azure artifacts, generate the synthetic source data, and execute the end-to-end pipeline.

> **Important:** This is a portfolio project using synthetic data. Azure resource names, storage paths, workspace identifiers, linked services, and other environment-specific values must be configured for your own Azure subscription before execution.

---

## 1. Prerequisites

### Local tools

Install:

- Git
- Python 3.10+ recommended
- A modern web browser
- Azure CLI (recommended for deployment/administration)

### Azure services

The solution is designed around:

- Azure Data Lake Storage Gen2
- Azure Databricks
- Azure Data Factory
- Azure Synapse Analytics
- Azure Key Vault (recommended for secrets)

You need sufficient permissions to create/configure these resources or access an existing project environment.

---

## 2. Clone the Repository

```bash
git clone https://github.com/Jeevananda-Reddy-Busi/bankaml-de-project.git
cd bankaml-de-project
```

---

## 3. Generate Synthetic Source Data

The project includes a reproducible banking-data generator under:

```text
seed_data/
└── NorthBridge Bank AML generate_seed_data.py
```

The generator creates synthetic customers, branches, accounts, and transactions and intentionally injects data-quality issues and AML-like patterns.

Run it with the Python interpreter appropriate for your environment. If the generator requires third-party packages in your checked-out version, install those packages in your local virtual environment before execution.

Example virtual environment setup:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Review the generator before running it so the output directory matches the ADLS landing path configured for your environment.

---

## 4. Configure ADLS Gen2

Create or identify an ADLS Gen2 storage account and filesystem/container for the project.

A practical layout is:

```text
<container>/
├── landing/
│   ├── customers/
│   ├── accounts/
│   ├── branches/
│   └── transactions/
│
├── bronze/
├── silver/
├── gold/
└── quarantine/
```

Upload the generated source files to the appropriate landing locations.

Do not commit credentials, connection strings, access keys, or other secrets to Git.

---

## 5. Configure Azure Databricks

Create or use an Azure Databricks workspace with a cluster/runtime capable of running the notebooks in this repository.

Import or open the notebooks from:

```text
notebooks/
├── 01_bronze/
├── 02_silver/
├── 03_gold/
└── 04_utils/
```

Configure the storage/catalog paths and authentication mechanism for your environment.

For production-style deployments, prefer managed identities, service principals, Unity Catalog permissions, and/or Azure Key Vault rather than hard-coded credentials.

---

## 6. Execute Bronze

Run the Bronze notebooks in:

```text
notebooks/01_bronze/
```

Recommended order:

```text
bronze_util.ipynb
        ↓
bronze_branches.ipynb
bronze_customers.ipynb
bronze_accounts.ipynb
bronze_transactions.ipynb
```

The exact execution dependency should follow the ADF pipeline configuration in:

```text
adf/pipeline/pl_bronze.json
```

Expected outcome:

- Source files are read from the configured landing area.
- Bronze Delta datasets are created/updated.
- Source data is preserved with minimal transformation.

---

## 7. Execute Silver

Run the reusable utilities and Silver notebooks:

```text
notebooks/04_utils/
notebooks/02_silver/
```

The Silver layer performs validation, deduplication, standardization, enrichment, quarantine, incremental processing, and historical tracking.

Pay particular attention to:

```text
notebooks/04_utils/watermark_incremental_load.ipynb
```

This demonstrates the control-table/watermark pattern used to identify data that needs processing.

Expected outputs include trusted Silver Delta datasets and quarantine datasets for records that fail critical validation rules.

---

## 8. Execute Gold

Run the Gold notebooks in:

```text
notebooks/03_gold/
```

Recommended reading/execution order:

```text
gold_structuring_detection.ipynb
gold_rapid_inout_detection.ipynb
gold_customer_risk_summary.ipynb
gold_account_daily_txn_summary.ipynb
```

The Gold layer produces AML detection and analytical datasets.

---

## 9. Configure Azure Data Factory

The source-controlled ADF artifacts are under:

```text
adf/
```

Key components include:

```text
adf/
├── factory/
├── linkedService/
└── pipeline/
    ├── pl_master.json
    ├── pl_bronze.json
    ├── pl_silver.json
    └── pl_gold.json
```

Configure the linked services for your environment, including Databricks and Key Vault where applicable.

### Master execution

The intended flow is:

```text
pl_master
   ↓
pl_bronze
   ↓ success
pl_silver
   ↓ success
pl_gold
```

Use the master pipeline for the end-to-end run after individual layers have been validated.

---

## 10. ADF Deployment Artifacts

The repository also contains generated deployment templates under:

```text
adf-bankaml-dev/
```

These artifacts can be used as a reference for deploying the factory configuration into an Azure environment.

Before deployment, review parameter files and replace environment-specific values rather than copying development settings blindly into another environment.

---

## 11. Configure Synapse Analytics

The Synapse artifacts are under:

```text
synapse/
```

The SQL scripts define external tables over selected Gold Delta datasets.

Review:

```text
synapse/sqlscript/
```

The environment must have the required external data source and Delta file-format configuration before the external tables are created.

Example serving flow:

```text
Gold Delta data
      ↓
Synapse external table
      ↓
SQL query / analytics
```

The repository also contains Synapse deployment artifacts under:

```text
syn-bankaml-dev/
```

---

## 12. End-to-End Execution

Once the Azure resources and environment-specific configuration are ready:

```text
1. Generate synthetic source data
            ↓
2. Upload source files to ADLS landing
            ↓
3. Run ADF pl_master
            ↓
4. Bronze ingestion
            ↓
5. Silver validation + enrichment + incremental processing
            ↓
6. Gold AML detection + summaries
            ↓
7. Synapse external tables
            ↓
8. Run SQL validation queries
```

---

## 13. Validation Checklist

After the run, verify:

### Bronze

- Source datasets exist as Delta tables.
- Record counts are plausible.
- Raw transaction records are available.

### Silver

- Invalid records are quarantined.
- Duplicate records are handled.
- Currency and timestamps are standardized.
- USD enrichment is populated where applicable.
- Incremental processing uses the expected watermark.
- Historical records are maintained for tracked entities.

### Gold

- Structuring flags are generated from the demonstration rules.
- Rapid in/out flags are generated.
- Customer risk summaries contain expected aggregations.
- Daily account summaries are unique at the intended account/date grain.

### Synapse

- External tables resolve successfully.
- SQL queries return Gold data.
- No unnecessary physical copy of the Delta Gold datasets is required for the external-table use cases.

---

## 14. Troubleshooting Guide

### Authentication failures

Check:

- Azure identity/permissions.
- Databricks authentication.
- ADF linked services.
- Key Vault access.
- Storage permissions.

Avoid putting credentials directly into notebooks or JSON files.

### Empty or missing Delta tables

Check:

- ADLS landing path.
- Storage permissions.
- Notebook configuration.
- Catalog/schema/table names.
- Whether the Bronze pipeline completed successfully.

### Silver records unexpectedly quarantined

Inspect the quarantine dataset and review:

- `quarantine_reason`
- `quarantined_at`
- `source_layer`

Then trace the record back to the relevant validation rule.

### Incremental load does not process new data

Check:

- Watermark control table.
- Watermark column.
- Last processed value.
- Source timestamps/values.
- Whether the previous pipeline run completed successfully.

### Gold AML output is empty

Remember that AML detection uses deliberately simplified demonstration rules. Verify that the synthetic generator produced the intended AML-like patterns and that Silver transaction timestamps and amounts were standardized correctly.

### Synapse external table fails

Check:

- External data source configuration.
- Delta file format definition.
- Storage access.
- Gold table/location.
- Database/schema selection.

---

## 15. Security Checklist

Before pushing or deploying:

- [ ] No passwords or access keys are committed.
- [ ] No connection strings containing secrets are committed.
- [ ] No real customer data is used.
- [ ] Environment-specific values are parameterized.
- [ ] Production deployments use secure identity/authentication mechanisms.
- [ ] Access follows least-privilege principles.

---

## 16. Recommended Learning Path

If you are new to the project, do not start by running everything at once.

Follow this order:

```text
PROJECT_REQUIREMENTS.md
        ↓
ARCHITECTURE.md
        ↓
seed_data/
        ↓
01_bronze/
        ↓
04_utils/
        ↓
02_silver/
        ↓
03_gold/
        ↓
adf/pipeline/
        ↓
synapse/sqlscript/
```

This mirrors the way a Data Engineer can reason about the solution: **requirements → architecture → source → ingestion → trusted data → business outputs → orchestration → serving**.
