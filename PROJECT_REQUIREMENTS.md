# Bank AML Data Engineering Platform — Project Requirements Specification

> **Portfolio implementation:** This document presents the business and technical requirements that the repository is designed to satisfy. It is written in a client-style format so a new engineer can understand the expected solution before reading the implementation.

## 1. Project Overview

### 1.1 Objective

Design and implement a cloud-based data engineering platform for a banking organization to consolidate customer, account, branch, and transaction data and produce trusted analytical datasets for Anti-Money Laundering (AML) monitoring.

The platform must support reliable ingestion, data-quality processing, incremental loads, historical tracking, AML pattern detection, customer-level risk aggregation, and SQL-based analytical access.

### 1.2 Business Outcome

The solution should enable downstream analysts and compliance teams to:

- Work with standardized and trusted banking data.
- Identify transaction patterns that warrant AML review.
- Review customer-level transaction and flag activity.
- Analyze daily account transaction behavior.
- Query curated Gold datasets through SQL.

> **Scope note:** This repository uses synthetic data and simplified AML rules for portfolio/learning purposes. It is not a production AML compliance solution.

---

## 2. Source Data Requirements

The platform must process the following source entities:

| Dataset | Business purpose | Expected source format |
|---|---|---|
| Customers | Customer master and risk attributes | CSV |
| Accounts | Customer account information | CSV |
| Branches | Branch reference information | CSV |
| Transactions | Account-level transaction activity | CSV |
| FX Rates | Currency conversion reference data | Notebook-generated/reference dataset |

The project must include a reproducible synthetic-data generator so the end-to-end solution can be demonstrated without real banking data.

---

## 3. Data Lake Requirements

The solution must use a cloud data lake as the central storage layer and organize processing using a **Bronze → Silver → Gold** architecture.

### 3.1 Bronze requirements

- Ingest source files with minimal business transformation.
- Preserve source-level information required for downstream processing.
- Apply explicit Spark schemas where appropriate.
- Store ingested datasets as Delta tables.

### 3.2 Silver requirements

The Silver layer must produce trusted and standardized datasets.

Required processing includes:

- Data-type standardization.
- Mandatory-field validation.
- Duplicate detection and removal.
- Referential-integrity validation.
- Currency normalization.
- Timestamp normalization.
- FX enrichment and USD amount calculation.
- Controlled defaulting of selected missing attributes.
- Data-quality quarantine for invalid records.
- Audit metadata.
- Hash-based change detection.
- Historical tracking for applicable entities.
- Incremental Delta `MERGE` processing.

### 3.3 Gold requirements

The Gold layer must contain business-ready datasets supporting AML analysis and operational reporting.

Required outputs:

1. Structuring detection results.
2. Rapid in/out detection results.
3. Customer risk summary.
4. Account daily transaction summary.

---

## 4. Data Quality Requirements

Invalid records must not be silently dropped.

Where a record fails a critical validation rule, the solution should:

1. Identify the validation failure.
2. Preserve the invalid record in a quarantine dataset.
3. Record a meaningful quarantine reason.
4. Record when the record was quarantined.
5. Identify the originating processing layer/source.

The quality framework should make failures traceable and support operational troubleshooting.

---

## 5. Incremental Processing Requirements

The platform must support batch-incremental processing so previously processed data does not need to be reprocessed unnecessarily.

A reusable watermark/control mechanism should maintain metadata such as:

- Schema name.
- Table name.
- Source.
- Watermark column.
- Last processed value.
- Active/inactive status.
- Updated timestamp.

### Expected processing pattern

```text
Read last processed watermark
            ↓
Identify newly arrived/changed source records
            ↓
Validate and transform
            ↓
Merge successful records into Delta tables
            ↓
Update the watermark only after successful processing
```

---

## 6. Historical Data Requirements

Selected master entities must support historical change tracking using an **SCD Type 2-style** pattern.

When a tracked attribute changes, the solution should:

- Detect the change using a deterministic comparison/hash.
- Expire the previous version.
- Create a new version of the record.
- Maintain effective start/end dates.
- Identify the current version.

The design must allow historical and current-state analysis without losing previous versions.

---

## 7. AML Detection Requirements

### AML-001 — Structuring Detection

Identify transaction behavior resembling structuring/smurfing by detecting multiple deposits near a reporting threshold within a short time window.

The portfolio implementation uses the following demonstration parameters:

- Reporting threshold: **$10,000**.
- Detection window: **48 hours**.
- Near-threshold range: **85%–99% of the threshold**.
- Minimum clustered near-threshold deposits: **3**.

The resulting dataset should provide sufficient information for an analyst to understand the detected pattern, including account/customer identifiers, transaction information, detection window, severity, and flag status.

### AML-002 — Rapid In/Out Detection

Identify an inflow followed by a substantial outflow from the same account within a short period.

The portfolio implementation uses:

- Maximum time gap: **24 hours**.
- Outflow threshold: **at least 85% of the inflow amount**.

The output should retain the related transaction identifiers, amounts, time gap, account/customer information, and a deterministic flag identifier.

### AML-003 — Customer Risk Summary

Create a customer-level analytical dataset combining:

- Stated risk rating.
- Account count.
- Total transaction volume in USD.
- Transaction count.
- AML flag count.
- Behavioral risk score.
- Priority review indicator.

The demonstration scoring model is:

| AML flag count | Behavioral risk | Priority review |
|---:|---|---|
| 0–1 | Low | No |
| 2 | Medium | No |
| 3+ | High | Yes |

> These thresholds are illustrative portfolio rules and must not be interpreted as regulatory guidance.

---

## 8. Analytical Reporting Requirements

The platform must produce an account/day aggregate containing:

- Account ID.
- Customer ID.
- Branch ID.
- Transaction date.
- Transaction count.
- Total deposits in USD.
- Total withdrawals in USD.
- Net flow in USD.
- Account status/activity mismatch indicator.
- A deterministic composite key.

The dataset must be suitable for downstream SQL analytics and reporting.

---

## 9. Orchestration Requirements

Azure Data Factory must orchestrate the complete processing workflow.

The orchestration should enforce layer dependencies:

```text
                    pl_master
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      pl_bronze     pl_silver     pl_gold
          │            │            │
       Bronze        Silver        Gold
      notebooks     notebooks    notebooks
```

Required behavior:

- Bronze must complete successfully before Silver begins.
- Silver must complete successfully before Gold begins.
- Notebook dependencies within each layer should be explicit.
- Failure in an upstream layer should prevent dependent downstream processing.

---

## 10. SQL Serving Requirements

Curated Gold Delta datasets must be accessible through Azure Synapse Analytics SQL.

The solution should demonstrate **external tables over Delta data** for selected Gold datasets, avoiding unnecessary duplication of the Gold data into separate physical warehouse tables for these use cases.

Required examples include datasets such as:

- `account_daily_txn_summary`
- `customer_risk_summary`
- AML flag outputs

---

## 11. Security Requirements

The repository must not contain real customer information or production secrets.

For a production implementation:

- Secrets should be stored in a secure secret-management service such as Azure Key Vault.
- Managed identities/service principals should be preferred over embedded credentials.
- Connection details should be parameterized rather than hard-coded.
- Access to sensitive banking data should follow least-privilege principles.

---

## 12. Non-Functional Requirements

| Area | Requirement |
|---|---|
| Scalability | Use distributed processing suitable for large datasets. |
| Reliability | Implement dependency-aware orchestration and controlled failure handling. |
| Data quality | Validate, quarantine, and audit rejected records. |
| Performance | Prefer incremental processing over unnecessary full reloads. |
| Maintainability | Keep reusable processing logic and clear layer boundaries. |
| Auditability | Preserve processing metadata and historical context where required. |
| Reproducibility | Synthetic source generation must be repeatable. |
| Security | Do not commit real credentials or customer information. |
| Source control | Store notebooks, pipelines, SQL, and deployment artifacts in Git. |

---

## 13. Expected Deliverables

The completed solution should provide:

- Synthetic banking source-data generator.
- Bronze Delta ingestion notebooks.
- Silver cleansing and standardization notebooks.
- Data-quality quarantine framework.
- Watermark-based incremental processing framework.
- SCD Type 2-style historical processing.
- Gold AML detection notebooks.
- Customer risk summary.
- Account daily transaction summary.
- Azure Data Factory orchestration pipelines.
- Synapse SQL external-table definitions.
- Azure deployment artifacts.
- Technical documentation for setup and architecture.

---

## 14. Acceptance Criteria

The implementation can be considered complete when a new engineer can:

1. Generate the synthetic banking source data.
2. Load the data through the Bronze layer.
3. Execute Silver validation, enrichment, incremental, and historical processing.
4. Produce Gold AML and reporting datasets.
5. Execute the workflow through the ADF master pipeline.
6. Query selected Gold datasets through Synapse SQL external tables.
7. Trace invalid records through quarantine outputs.
8. Understand the complete solution using the repository documentation.

---

## 15. Implementation Reference

The requirements above map to the repository as follows:

```text
PROJECT_REQUIREMENTS.md
        │
        ├── SETUP.md
        │       └── How to deploy and execute
        │
        ├── ARCHITECTURE.md
        │       └── How the platform is designed
        │
        ├── seed_data/
        │       └── Synthetic source generation
        │
        ├── notebooks/
        │       ├── 01_bronze/
        │       ├── 02_silver/
        │       ├── 03_gold/
        │       └── 04_utils/
        │
        ├── adf/
        │       └── End-to-end orchestration
        │
        └── synapse/
                └── SQL serving layer
```
