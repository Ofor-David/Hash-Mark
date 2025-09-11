# HashMark — Serverless Proof‑of‑Existence on Azure

[![Build](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](./.github/workflows/ci.yml) [![License](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE) [![Runtime](https://img.shields.io/badge/Azure%20Functions-Python%203.12-0078D4)](https://learn.microsoft.com/azure/azure-functions/)

HashMark is a lightweight, serverless platform that lets you prove a digital file existed at a specific point in time without revealing its contents. When a file is uploaded to Azure Blob Storage, an Azure Function computes cryptographic hashes and stores a tamper‑evident record in Azure Table Storage. A simple HTTP API verifies later whether a given file (or hash) was previously recorded.

- **Cloud Platform**: Microsoft Azure
- **IaC**: Terraform
- **Compute**: Azure Functions (Python)
- **Storage**: Azure Blob Storage (uploads) + Azure Table Storage (hash records)
- **Libraries**: `azure-functions`, `azure-data-tables`, `requests-toolbelt`
- **Architecture**: Serverless, event-driven (Blob upload → Hash → Persist)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Infrastructure Setup](#infrastructure-setup)
- [Source Code Structure](#source-code-structure)
- [Installation and Deployment](#installation-and-deployment)
- [API Documentation](#api-documentation)
- [Configuration and Environment](#configuration-and-environment)
- [Troubleshooting and FAQ](#troubleshooting-and-faq)
- [License and Legal](#license-and-legal)

---

## Project Overview

- **Problem**: Traditional notarization is slow, costly, and requires sharing document contents. Many workflows only need to prove a file existed unchanged at a point in time.
- **Solution**: HashMark computes and stores cryptographic file digests on upload and exposes verification APIs. Only hashes and minimal metadata are stored—never file contents—preserving privacy while enabling integrity proofs.
- **Value**:
  - Low‑cost, automatic, and privacy‑preserving proof‑of‑existence
  - Serverless scaling and pay‑per‑use economics
  - Simple API integration and straightforward operations
- **Use cases**:
  - Legal and compliance document sealing
  - Intellectual property and authorship proofs
  - Supply‑chain and audit logs
  - Medical images and research data integrity

High‑level architecture (ASCII):

```
+-----------------------------+           +-----------------------+
|  Client / Uploader          |           |  Verifier / API User  |
+--------------+--------------+           +-----------+-----------+
               |                                      |
               | 1) Upload file                       | 4) POST /api/verify (hash or file)
               v                                      v
        +------+-----------------+            +-------+-----------------+
        | Azure Blob Storage     |            | Azure Functions (HTTP) |
        | Container: uploads     |            | Route: /api/verify     |
        +-----------+------------+            +-----------+------------+
                    | 2) Blob-created trigger                |
                    v                                         |
            +-------+-----------------------+                  |
            | Azure Functions (Blob Trigger)|                  |
            | Compute SHA-256/SHA3, store   |                  |
            +---------------+---------------+                  |
                            | 3) Upsert record                 |
                            v                                  |
                   +--------+-------------------+              |
                   | Azure Table Storage       |<--------------+
                   | Hash + metadata + times   |
                   +---------------------------+
```

---

## Features

- **Automatic hashing on upload**: SHA‑256 (and SHA3‑256 stored alongside) computed on every blob written to `uploads/`.
- **Verification API**: Verify by providing either a SHA‑256 hash or uploading a file via multipart form.
- **Privacy‑preserving**: Only digests and metadata are stored; original file bytes remain in private blob storage and are not returned.
- **Detailed results**: Responses include timestamps, file size, and storage row identifiers.
- **Serverless scale**: Azure Functions on a consumption plan scale to demand.
- **JSON responses**: Simple, consistent API payloads.

---

## System Architecture

- **Data flow**:
  1. A file is uploaded to Blob Storage container `uploads`.
  2. A Blob Trigger Function reads the bytes, computes SHA‑256 and SHA3‑256, and writes a record to Table Storage with partition and row keys, timestamps, and metadata.
  3. A user later calls the HTTP endpoint with a hash or an uploaded file; the Function queries Table Storage for a match and returns verification details.
- **Components**:
  - Azure Blob Storage: private `uploads` container for ingestion
  - Azure Functions: Blob trigger (`uploads/{name}`) and HTTP route `/api/verify`
  - Azure Table Storage: records containing `sha256_hash`, `sha3_hash`, file size, timestamps, and keys
- **Events & triggers**: Blob creation triggers hashing; HTTP trigger performs verification.
- **Security model**:
  - Storage accounts are private; only Functions access data via connection strings
  - No file contents are exposed via the API; only hashes and metadata are returned
  - Secrets are stored in app settings
- **Scalability**:
  - Consumption plan autoscales Function instances
  - Table queries are partition‑aware; partitioning by date improves scan performance
  - Blob and Table Storage scale horizontally with Azure limits

---

## Infrastructure Setup

Terraform modules provision:

- Resource Group, Storage Account, `uploads` Blob container, and Table Storage (`<name_prefix>Records`)
- Linux Function App on a consumption plan (Python 3.12)
- Optional Service Principal with Contributor role for CI/CD

Resource naming and inputs (from `terraform/variables.tf`):

- `name_prefix` (string): Prefix for all resource names
- `region` (string): Azure region
- `storage_account_name` (string): Globally unique storage account name for main data
- `subscription_id` (string): Target subscription

Primary outputs include:

- Storage connection string
- Table name
- Resource group information
- Function‑scoped storage account
- Optional GitHub Actions SP credentials (sensitive)

Typical Terraform workflow using `terraform.tfvars`:

```bash
# 0) Prepare variables file (run in repo root)
touch terraform/terraform.tfvars
# Edit terraform/terraform.tfvars with your values

# 1) Authenticate
az login
az account set --subscription <SUBSCRIPTION_ID>

# 2) Initialize and review plan (from ./terraform)
cd terraform
terraform init
terraform plan    # vars are loaded from terraform.tfvars automatically

# 3) Apply
terraform apply -auto-approve
```

Optional: keep multiple env files and use `-var-file`:

```bash
terraform plan -var-file="envs/dev.tfvars"
terraform apply -var-file="envs/dev.tfvars"
```

Cost and sizing:

- Consumption Functions: pay per execution and GB‑s
- Storage: minimal costs for blob + table operations; budget for egress if applicable

Permissions and CLI:

- Requires Owner/Contributor on the target subscription or delegated RG
- AzureAD permissions are needed if creating a Service Principal

---

## Source Code Structure

```
hashmark/
├── terraform/                # Terraform configurations (RG, Storage, Function, SP)
│   ├── main.tf
│   ├── variables.tf
│   ├── provider.tf
│   └── modules/
├── hashmark-func/            # Azure Functions source
│   ├── function_app.py       # blob trigger + /api/verify
│   ├── host.json             # Functions host configuration
│   ├── requirements.txt      # Python deps
├── .github/                  # (CI/CD) workflows and templates
└── README.md                 # This file
```

---

## Installation and Deployment

Prerequisites:

- Python 3.12 (matches Function App setting)
- Azure CLI ≥ 2.50, Terraform ≥ 1.6
- Azure subscription with permissions
- Node.js (optional) for Azure Functions Core Tools UI

**Deploy infrastructure with Terraform: see [Infrastructure Setup](#infrastructure-setup).**

Deploy the Function App:
GitHub Actions (recommended): Builds and publishes on push.

Environment variables (App Settings):

- `FUNCTIONS_WORKER_RUNTIME=python`
- `AzureWebJobsStorage=<connection string to main storage>`
- `TABLE_NAME=<name_prefix>Records`

Verification checklist:

- Blob container `uploads` exists and is private
- Table `<name_prefix>Records` exists
- HTTP `POST /api/verify` returns 400 for invalid content type and 200 for valid requests

---

## API Documentation

Base URL: `https://<function-app-name>.azurewebsites.net`

### Verify (hash or file)

- **POST** `/api/verify`
- Content types: `application/json` (hash‑only) or `multipart/form-data` (file upload)

Request (hash‑only):

```http
POST /api/verify HTTP/1.1
Content-Type: application/json

{"hash":"<64-hex-sha256>"}
```

Response (200):

```json
{
  "success": true,
  "verification": {
    "exists": true,
    "file_details": {
      "original_filename": "uploads/mydoc.pdf",
      "file_size": 12345,
      "upload_timestamp": "2024-01-01T12:00:00Z",
      "sha256_hash": "...",
      "verification_count": 3,
      "last_verified": "2024-01-02T09:30:00Z"
    },
    "proof_details": {
      "partition_key": "2024-01-01",
      "row_key": "1704100800_deadbeef",
      "storage_status": "verified"
    }
  },
  "request_info": {
    "provided_hash": "...",
    "verification_timestamp": "2024-01-02T09:30:00Z"
  }
}
```

Errors:

- 400: Unsupported content type, missing/invalid `hash`
- 500: Internal server error

Curl examples:

```bash
# Hash-only
curl -X POST https://<function-app-name>.azurewebsites.net/api/verify \
  -H "Content-Type: application/json" \
  -d '{"hash":"<64-hex-sha256>"}' \

# Multipart file upload
curl -X POST https://<function-app-name>.azurewebsites.net/api/verify \
  -F "file=@filename" \

```

## Configuration and Environment

Environment variables / App Settings used by the Function:

- `FUNCTIONS_WORKER_RUNTIME` — set to `python`
- `AzureWebJobsStorage` — connection string to the primary Storage Account used by both blob and table access
- `TABLE_NAME` — name of the Azure Table to persist/query (e.g., `<name_prefix>Records`)

Templates to include:

- `hashmark-func/local.settings.json.template` (do not commit secrets):

```json
{
  "IsEncrypted": false,
  "Values": {
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AzureWebJobsStorage": "<connection-string>",
    "TABLE_NAME": "<prefix>Records"
  }
}
```

---

## Troubleshooting and FAQ

- Blob trigger not firing:
  - Ensure uploads go to container `uploads` (exact name)
  - Verify `AzureWebJobsStorage` and that the Function app has access
- 400 "Unsupported content type":
  - Use `application/json` (hash‑only) or `multipart/form-data` (file upload)
- Hash not found but file was uploaded:
  - Allow for eventual consistency; confirm trigger success in logs; check Table name
- Permissions errors with Terraform SP:
  - Confirm AzureAD provider permissions and subscription role assignments
- Performance tips:
  - Prefer hash‑only verification for very large files; enable HTTP keep‑alive on clients

---

## License and Legal

- License: MIT (see [`LICENSE`](./LICENSE))
- Dependencies: `azure-functions`, `azure-data-tables`, `requests-toolbelt` (see `hashmark-func/requirements.txt`)
- Privacy: Only hashes and metadata are stored; operators should publish a privacy notice
- Terms: If hosting for others, publish acceptable use and rate limits