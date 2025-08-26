# GOAL: Adapt my decoupled, configuration-driven Medallion pipeline to my existing project structure.
#
# MY PROJECT STRUCTURE:
# /dab-kafka
# |-- databricks.yml
# |-- pyproject.toml
# |-- resources/
# |   |-- nyc_taxi_job.yml  (This will define the job)
# |-- src/
# |   |-- engine/
# |   |   |-- __init__.py
# |   |   |-- main.py       (This will be our single, parameterized entry point)
# |   |   |-- utils.py      (Helper functions will go here)
#
# ARCHITECTURE:
# 1. DEPLOYMENT: Databricks Asset Bundle (DAB) using my existing structure.
# 2. CONFIGURATION: A new `config/data_products.yml` file will define the data product.
# 3. ENTRY POINT: A single script `src/engine/main.py` will accept a `--step` parameter ('bronze', 'silver', or 'gold') to run the logic for that specific layer.
# 4. ORCHESTRATION: The job in `resources/nyc_taxi_job.yml` will be a multi-task job where each task calls `main.py` with a different `--step` parameter.

#------------------------------------------------------------------------------------
# PART 1: THE CONFIGURATION & PRODUCER
#------------------------------------------------------------------------------------
#
# ---
# 1.1 `producer.py` (at the root of /dab-kafka)
# ---
# Create a standalone Python Kafka producer script.
# It should generate fake NYC Taxi Trip data and send it as JSON to an Azure Event Hub topic.
# After sending ~15 messages with an initial schema, simulate schema drift by adding a new field `tip_amount` (float).
#
# ---
# 1.2 `config/data_products.yml` (create this new directory and file)
# ---
# Create the YAML configuration file that defines our data product.
#
# data_products:
#   - product_name: "nyc_taxi_metrics"
#     source:
#       topic: "t_nyc_taxi_trips"
#     bronze:
#       path: "/mnt/medallion/taxi_metrics/bronze"
#       schema_string: >
#         vendor_id STRING, pickup_datetime STRING, dropoff_datetime STRING,
#         passenger_count INT, trip_distance DOUBLE, rate_code_id INT,
#         payment_type INT, fare_amount DOUBLE, tip_amount DOUBLE
#     silver:
#       path: "/mnt/medallion/taxi_metrics/silver"
#       transformations:
#         - "CAST pickup_datetime AS TIMESTAMP"
#         - "CAST dropoff_datetime AS TIMESTAMP"
#       enrichments:
#         - "ROUND((unix_timestamp(dropoff_datetime) - unix_timestamp(pickup_datetime)) / 60, 2) AS trip_duration_minutes"
#       filters:
#         - "fare_amount > 0 AND trip_distance > 0"
#     gold:
#       path: "/mnt/medallion/taxi_metrics/gold"
#       aggregation:
#         group_by: ["vendor_id"]
#         window:
#           time_column: "pickup_datetime"
#           duration: "10 minutes"
#         expressions:
#           - "sum(fare_amount) as total_fare"
#           - "avg(tip_amount) as avg_tip"
#           - "sum(trip_distance) as total_distance"

#------------------------------------------------------------------------------------
# PART 2: THE PYSPARK APPLICATION LOGIC (`src/engine/`)
#------------------------------------------------------------------------------------
#
# ---
# 2.1 `src/engine/utils.py`
# ---
# Create a helper function `get_product_config(product_name)` that reads `config/data_products.yml`,
# finds the entry matching `product_name`, and returns its configuration dictionary.
#
# ---
# 2.2 `src/engine/main.py`
# ---
# Create a single, parameterized PySpark application.
# 1. Use Python's `argparse` library to accept two command-line arguments:
#    - `--product-name` (e.g., "nyc_taxi_metrics")
#    - `--step` (a choice of "bronze", "silver", or "gold")
# 2. Import `get_product_config` from `.utils`.
# 3. Create three separate functions: `run_bronze(config)`, `run_silver(config)`, `run_gold(config)`.
#    - The logic for `run_bronze` should read from Kafka and write to the Bronze path, enabling schema evolution (`mergeSchema: true`).
#    - The logic for `run_silver` should read from Bronze, apply transformations from the config, and write to Silver.
#    - The logic for `run_gold` should read from Silver, apply aggregations from the config, and write to Gold.
# 4. In the main execution block (`if __name__ == "__main__":`), parse the arguments, load the config using the `product_name`, and call the correct `run_*` function based on the `step` argument.

#------------------------------------------------------------------------------------
# PART 3: DATABRICKS ASSET BUNDLE CONFIGURATION
#------------------------------------------------------------------------------------
#
# ---
# 3.1 `resources/nyc_taxi_job.yml` (replace new_project.job.yml)
# ---
# Create the YAML file that defines the multi-task Databricks job.
# 1. Define a job with three tasks: `bronze_task`, `silver_task`, `gold_task`.
# 2. The `silver_task` should depend on the `bronze_task`, and `gold_task` on `silver_task`.
# 3. Each task will be a `spark_python_task` that points to the SAME python file: `src/engine/main.py`.
# 4. Differentiate the tasks by passing different `parameters`.
#    - `bronze_task` parameters: `["--product-name", "nyc_taxi_metrics", "--step", "bronze"]`
#    - `silver_task` parameters: `["--product-name", "nyc_taxi_metrics", "--step", "silver"]`
#    - `gold_task` parameters: `["--product-name", "nyc_taxi_metrics", "--step", "gold"]`
# 5. The `bronze_task` should be configured to run continuously. The other tasks will trigger upon its successful completion.
#
# ---
# 3.2 `databricks.yml`
# ---
# Update the main bundle file to orchestrate everything.
# 1. Define the bundle name, e.g., `dab-kafka-bundle`.
# 2. Use an `include` statement to load the job definition from `resources/nyc_taxi_job.yml`.
# 3. Define a `sync` section under the `targets` block to ensure the `config/` directory is also bundled and sent to Databricks along with the `src/` code.
#
# Example `databricks.yml` structure:
#
# bundle:
#   name: dab-kafka-bundle
#
# include:
#   - resources/nyc_taxi_job.yml
#
# targets:
#   dev:
#     mode: development
#     default: true
#     sync:
#       - dest: /Shared/dabs/dab-kafka/{env.USER}
#         patterns:
#           - "config/**"
#           - "src/**"
#