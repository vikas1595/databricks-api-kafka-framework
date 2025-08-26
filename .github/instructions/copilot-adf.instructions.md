# GOAL: Create a configuration-driven, modular Terraform setup to deploy an Azure Data Factory (ADF) API ingestion pipeline.

# PROJECT CONTEXT:
# This Terraform code will be integrated into an existing project.
# It should assume that the core infrastructure (Resource Group, ADF instance, and ADLS Gen2 Storage Account) already exists.
# The Terraform code will only be responsible for deploying the ADF components (Linked Services, Datasets, Pipeline) and uploading the configuration file.

#------------------------------------------------------------------------------------
# PART 1: THE CONFIGURATION FILE
#------------------------------------------------------------------------------------
#
# ---
# 1.1 `adf/api_sources.yml`
# ---
# Create a YAML configuration file that defines the API sources to be ingested.
# Each source should have:
# - `source_name`: A unique identifier.
# - `api_url`: The full URL for the API endpoint.
# - `destination`: An object containing the output details.
#   - `container`: The ADLS container name (e.g., "raw").
#   - `path`: The base directory path for the ingested data.
#   - `file_name`: The name of the output file (e.g., "data.json").

# Example `adf/api_sources.yml`:
api_sources:
  - source_name: "open_brewery_db"
    api_url: "https://api.openbrewerydb.org/v1/breweries"
    destination:
      container: "raw"
      path: "open_brewery_db/breweries"
      file_name: "data.json"
  - source_name: "us_public_holidays"
    api_url: "https://date.nager.at/api/v3/PublicHolidays/2024/US"
    destination:
      container: "raw"
      path: "public_holidays/us_holidays_2024"
      file_name: "data.json"

#------------------------------------------------------------------------------------
# PART 2: THE TERRAFORM STRUCTURE (MODULAR APPROACH)
#------------------------------------------------------------------------------------
#
# Create a modular Terraform setup with the following directory structure:
# /terraform
# |-- main.tf
# |-- provider.tf
# |-- variables.tf
# |-- terraform.tfvars
# |-- outputs.tf
# |-- modules/
#     |-- adf_api_ingestion_pipeline/
#         |-- main.tf
#         |-- variables.tf
#         |-- outputs.tf

# ---
# 2.1 Root Terraform Files (`terraform/`)
# ---
# - `provider.tf`: Configure the Azure provider.
# - `variables.tf`: Define variables for existing resource names (`resource_group_name`, `data_factory_name`, `storage_account_name`).
# - `main.tf`:
#   1. Use `data` sources to look up the existing RG, ADF, and Storage Account.
#   2. Define an `azurerm_storage_container` resource to ensure the target container (e.g., "raw") exists.
#   3. Define an `azurerm_storage_blob` resource to upload the `api_sources.yml` file to a `config/` directory in the container.
#   4. Call the `adf_api_ingestion_pipeline` module, passing in the necessary outputs from the data sources (like `data_factory_id` and `storage_connection_string`).
# - `outputs.tf`: Output the `pipeline_name` from the module.

# ---
# 2.2 ADF Pipeline Module (`terraform/modules/adf_api_ingestion_pipeline/`)
# ---
# This module should encapsulate all the ADF-specific resources.
#
# - `variables.tf`: Define the module's input variables: `data_factory_id`, `storage_container_name`, and `storage_connection_string`.
#
# - `main.tf`: Create the following resources:
#   1. **Linked Services**:
#      - An `azurerm_data_factory_linked_service_web` for the dynamic HTTP source.
#      - An `azurerm_data_factory_linked_service_azure_blob_storage` for the sink.
#   2. **Datasets**:
#      - A `ds_api_config_file` to read the `api_sources.yml`.
#      - A `ds_http_dynamic_source` (`azurerm_data_factory_dataset_json`) configured with a `http_server_location`. Use non-empty placeholders for `path` and `filename` to pass validation. It should have a `RelativeURL` parameter.
#      - A `ds_adls_dynamic_sink` (`azurerm_data_factory_dataset_json`) with `dynamic_path_enabled` and `dynamic_filename_enabled` set to true. It should have `FolderPath` and `FileName` parameters.
#   3. **Pipeline (`azurerm_data_factory_pipeline`)**:
#      - Name the pipeline `pl_dynamic_api_ingestion`.
#      - Add `annotations` and `parameters` to the pipeline resource.
#      - Use the `activities_json` argument to define the pipeline logic:
#        - A `Lookup` activity (`LookupApiSources`) to read the config file.
#        - A `ForEach` activity (`ForEachApiSource`) that iterates over the output of the Lookup.
#        - Inside the `ForEach`, a nested `Copy` activity (`CopyApiData`).
#        - The `Copy` activity's sink (output) must dynamically construct a partitioned path using ADF expressions: `yyyy/MM/dd`. The expression should be: `@concat(item().destination.path, '/', formatDateTime(utcNow(), 'yyyy'), '/', formatDateTime(utcNow(), 'MM'), '/', formatDateTime(utcNow(), 'dd'))`.
#
# - `outputs.tf`: Output the `name` of the created `azurerm_data_factory_pipeline` resource.