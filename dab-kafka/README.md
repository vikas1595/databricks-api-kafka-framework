# Configuration-Driven Medallion Pipeline for Kafka on Databricks

This project implements a reusable, configuration-driven Medallion architecture for processing streaming data from Kafka using Databricks. The pipeline is designed to be easily adaptable to new data products by simply adding configuration files, without changing the core processing logic.

This example demonstrates the pipeline with a sample NYC Taxi dataset, reading from a Kafka topic and writing to Unity Catalog tables.

## Project Structure

```
/dab-kafka
|-- databricks.yml              # Main Databricks Asset Bundle configuration
|-- pyproject.toml              # Python project dependencies
|-- config/
|   |-- data_products.yml       # YAML definitions for one or more data products
|-- resources/
|   |-- nyc_taxi_job.yml        # Job definition for the NYC taxi data product
|-- src/
|   |-- engine/
|   |   |-- __init__.py
|   |   |-- main.py             # Parameterized PySpark entry point for all layers
|   |   |-- utils.py            # Helper function to read product configurations
|-- producer.py                 # Standalone Kafka producer for generating test data
```

## How it Works

The architecture is designed to decouple the pipeline logic from the data-specific configurations.

1.  **Configuration (`config/data_products.yml`)**: This file is the single source of truth for a data product. It defines everything from the source Kafka topic to the schemas, transformations, and aggregations for each layer (Bronze, Silver, Gold).

2.  **Generic Engine (`src/engine/main.py`)**: A single, parameterized PySpark script serves as the engine for all processing. It accepts a `--product-name` and `--step` (bronze, silver, or gold) as arguments. Based on these, it fetches the corresponding configuration from `data_products.yml` and executes the logic for that specific layer.

3.  **Orchestration (`resources/*.yml`)**: Each data product has its own job definition file. This file defines a multi-task job where each task calls the same `main.py` script but passes different `--step` parameters. This creates a dependency chain: the Silver task runs after Bronze, and Gold runs after Silver.

4.  **Deployment (`databricks.yml`)**: The main bundle file ties everything together. It builds the `src` directory into a Python wheel file and includes the job resource files for deployment.

## Getting Started

1.  **Install Dependencies**:
    This project uses Poetry for dependency management.
    ```bash
    poetry install
    ```

2.  **Configure Databricks CLI**:
    Ensure your Databricks CLI is configured to connect to your workspace.
    ```bash
    databricks configure
    ```

3.  **Deploy the Bundle**:
    Deploy the project to your Databricks workspace. This will build the wheel file, upload it, and create the `nyc_taxi_job`.
    ```bash
    databricks bundle deploy --target dev
    ```
    *(Note: `dev` is the default target)*

4.  **Run the Job**:
    You can run the job directly from the command line:
    ```bash
    databricks bundle run nyc_taxi_job
    ```
    Alternatively, find the job named `[dev your_name] nyc_taxi_job` in your Databricks workspace under **Workflows**.

## Tutorial: Adding a New Data Product

Let's add a new pipeline for "SF Bike Share" data.

#### Step 1: Define the New Product in `config/data_products.yml`

Open `config/data_products.yml` and add a new entry to the `data_products` list.

```yaml
# ... existing nyc_taxi_metrics product ...
- product_name: "sf_bike_share"
  source:
    topic: "t_sf_bike_trips"
  bronze:
    table: "dbx_data_platform_dev_2885690652894387.bronze.sf_bike_share"
    checkpoint_path: "/Volumes/dbx_data_platform_dev_2885690652894387/bronze/internal_files/checkpoints/sf_bike_share_bronze"
    schema_string: >
      trip_id INT, start_date STRING, start_station_name STRING,
      end_date STRING, end_station_name STRING, duration_sec INT
  silver:
    table: "dbx_data_platform_dev_2885690652894387.silver.sf_bike_share"
    checkpoint_path: "/Volumes/dbx_data_platform_dev_2885690652894387/silver/internal_files/checkpoints/sf_bike_share_silver"
    transformations:
      - "CAST(start_date AS TIMESTAMP) as start_date"
      - "CAST(end_date AS TIMESTAMP) as end_date"
    enrichments:
      - "ROUND(duration_sec / 60, 2) AS duration_minutes"
    filters:
      - "duration_sec > 0"
  gold:
    table: "dbx_data_platform_dev_2885690652894387.gold.sf_bike_share_analytics"
    checkpoint_path: "/Volumes/dbx_data_platform_dev_2885690652894387/gold/internal_files/checkpoints/sf_bike_share_gold"
    aggregation:
      group_by: ["start_station_name"]
      expressions:
        - "count(trip_id) as total_trips"
        - "avg(duration_minutes) as avg_duration"
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