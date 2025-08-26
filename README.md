# Configuration-Driven Medallion Pipeline with ADF and Databricks

This project implements an end-to-end data pipeline combining Azure Data Factory for API ingestion and Databricks for data processing using a Medallion architecture. The pipeline is configuration-driven, making it easily adaptable to new data sources and transformations.

## Quick Start Example

### 1. Configure Data Pipeline
```json
// adf/api_sources.json
[
  {
    "base_url": "https://api.example.com",
    "relative_url": "/v1/nyc-taxi",
    "destination": {
      "path": "raw/nyc_taxi",
      "file_name": "@formatDateTime(utcnow(), 'yyyy/MM/dd')/data.json"
    }
  }
]
```

```yaml
# dab-kafka/config/data_products.yml
- product_name: "nyc_taxi_metrics"
  source:
    topic: "t_nyc_taxi"
  bronze:
    table: "dbx_data_platform_dev.bronze.nyc_taxi"
    schema_string: "trip_id INT, pickup_time STRING, trip_distance DOUBLE"
  silver:
    table: "dbx_data_platform_dev.silver.nyc_taxi"
    transformations:
      - "CAST(pickup_time AS TIMESTAMP) as pickup_time"
  gold:
    table: "dbx_data_platform_dev.gold.nyc_taxi_analytics"
    aggregation:
      group_by: ["hour(pickup_time)"]
      expressions: ["avg(trip_distance) as avg_distance"]
```

### 2. Deploy and Run
```bash
# Deploy infrastructure
cd terraform && terraform apply

# Deploy Databricks components
cd ../dab-kafka && databricks bundle deploy

# Run pipeline
az datafactory pipeline create-run --name pl_dynamic_api_ingestion
databricks bundle run nyc_taxi_job
```

## Project Structure
```
.
├── adf/
│   └── api_sources.json          # API ingestion configuration
├── dab-kafka/                    # Databricks Asset Bundle
│   ├── config/
│   │   ├── data_products.yml     # Data product definitions
│   │   └── nyc_taxi_metrics.yml  # NYC taxi specific config
│   ├── src/
│   │   └── engine/              # Core processing logic
│   │       ├── main.py          # Main entry point
│   │       ├── gold.py          # Gold layer transformations
│   │       └── utils.py         # Helper functions
│   ├── resources/
│   │   └── nyc_taxi_job.yml     # Job definition
│   └── databricks.yml           # Bundle configuration
└── terraform/                    # Infrastructure as Code
    ├── modules/
    │   └── adf_api_ingestion_pipeline/
    │       ├── main.tf          # ADF pipeline module
    │       └── pipeline_activities.json.tpl
    ├── main.tf                  # Main infrastructure
    └── variables.tf             # Variable definitions
```

## How it Works

The architecture is designed to decouple the pipeline logic from the data-specific configurations.

1.  **Configuration (`config/data_products.yml`)**: This file is the single source of truth for a data product. It defines everything from the source Kafka topic to the schemas, transformations, and aggregations for each layer (Bronze, Silver, Gold).

2.  **Generic Engine (`src/engine/main.py`)**: A single, parameterized PySpark script serves as the engine for all processing. It accepts a `--product-name` and `--step` (bronze, silver, or gold) as arguments. Based on these, it fetches the corresponding configuration from `data_products.yml` and executes the logic for that specific layer.

3.  **Orchestration (`resources/*.yml`)**: Each data product has its own job definition file. This file defines a multi-task job where each task calls the same `main.py` script but passes different `--step` parameters. This creates a dependency chain: the Silver task runs after Bronze, and Gold runs after Silver.

4.  **Deployment (`databricks.yml`)**: The main bundle file ties everything together. It builds the `src` directory into a Python wheel file and includes the job resource files for deployment.

## Architecture

```mermaid
graph LR
    API[REST APIs] --> ADF[Azure Data Factory]
    ADF --> ADLS[Azure Storage]
    ADLS --> DBX[Databricks]
    DBX --> Bronze
    Bronze --> Silver
    Silver --> Gold
```

## Architecture Components

### 1. Data Ingestion Layer (Azure Data Factory)
- Configuration-driven REST API ingestion pipeline
- Supports multiple API sources through JSON configuration
- Dynamic path and file name handling
- Built-in error handling and monitoring

### 2. Processing Layer (Databricks)
- Unified analytics platform for batch and stream processing
- Medallion architecture for data refinement
- Scalable and collaborative environment

## Component Details

### API Ingestion (ADF)
The ingestion pipeline supports:
- Multiple API endpoints
- Dynamic file paths and names
- Configurable batch sizes
- Error handling and retries

### Data Processing (Databricks)
The processing pipeline implements:
- Bronze: Raw data preservation
- Silver: Cleaned and conformed data
- Gold: Business-level aggregations

## Monitoring and Troubleshooting

### Data Factory Pipeline
- Monitor pipeline runs in ADF Studio
- Check activity logs for detailed execution status
- Review output files in the storage container

### Databricks Processing
- Monitor job runs in Databricks Jobs UI
- Review logs for each task in the job
- Check output tables in Unity Catalog

## Development Guide

### Adding a New API Source
1. Add source configuration to `adf/api_sources.json`
2. Define schema in `dab-kafka/config/data_products.yml`
3. Create job definition in `dab-kafka/resources/`
4. Deploy changes:
   ```bash
   terraform apply  # For ADF changes
   databricks bundle deploy  # For Databricks changes
   ```

## Getting Started

### Prerequisites
```bash
# Install required tools
brew install terraform azure-cli databricks-cli poetry

# Login to Azure
az login

# Configure Databricks CLI
databricks configure --token
```

### 1. Infrastructure Setup
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars  # Edit with your values
terraform init
terraform apply
```

#### Step 2: Create a New Job Definition File

Create a new file `resources/sf_bike_job.yml`. You can copy `nyc_taxi_job.yml` and simply change the `name` and the `--product-name` parameter in each task.

```yaml
# resources/sf_bike_job.yml
resources:
  jobs:
    sf_bike_job:
      name: "sf_bike_job"
      tasks:
        - task_key: "bronze_task"
          spark_python_task:
            python_file: "src/engine/main.py"
            parameters: ["--product-name", "sf_bike_share", "--step", "bronze"]
          # ... other task config
        - task_key: "silver_task"
          depends_on:
            - task_key: "bronze_task"
          spark_python_task:
            python_file: "src/engine/main.py"
            parameters: ["--product-name", "sf_bike_share", "--step", "silver"]
          # ... other task config
        - task_key: "gold_task"
          depends_on:
            - task_key: "silver_task"
          spark_python_task:
            python_file: "src/engine/main.py"
            parameters: ["--product-name", "sf_bike_share", "--step", "gold"]
          # ... other task config
      # ... environments config ...
```

#### Step 3: Include the New Job in `databricks.yml`

Open `databricks.yml` and add the new job file to the `include` section.

```yaml
# databricks.yml
# ...
include:
  - resources/nyc_taxi_job.yml
  - resources/sf_bike_job.yml # <-- Add this line
# ...
```

#### Step 4: Deploy and Run

Deploy the bundle again to create the new job.

```bash
databricks bundle deploy
```

You can now run your new bike share pipeline:

```bash
databricks bundle run sf_bike_job
```

You have successfully added a new data pipeline without writing any new PySpark code!