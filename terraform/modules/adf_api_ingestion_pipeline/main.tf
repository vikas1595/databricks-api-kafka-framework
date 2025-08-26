locals {
  pipeline_name = "pl_dynamic_api_ingestion"
  dataset_names = {
    rest_source = "RestResource1"
    config      = "ds_api_config_file"
    sink        = "ds_adls_dynamic_sink"
  }
}

# REST source linked service
resource "azurerm_data_factory_linked_custom_service" "rest_source" {
  name            = "ls_rest_dynamic_source"
  data_factory_id = var.data_factory_id
  type            = "RestService"
  description     = "Dynamic REST API source connector"

  type_properties_json = jsonencode({
    "url"                               = "@{linkedService().base_url}",
    "authenticationType"                = "Anonymous",
    "enableServerCertificateValidation" = true
  })

  parameters = {
    "base_url" = "https://placeholder.com"
  }
}

# ADLS sink linked service
resource "azurerm_data_factory_linked_service_azure_blob_storage" "adls_sink" {
  name              = "AdlsSinkLinkedService"
  data_factory_id   = var.data_factory_id
  connection_string = var.storage_connection_string
}

# 3. Create the main ingestion pipeline
resource "azurerm_data_factory_pipeline" "ingestion_pipeline" {
  name            = local.pipeline_name
  data_factory_id = var.data_factory_id
  description     = "Configuration-driven REST API ingestion pipeline"

  parameters = {
    trigger_run_id = "optional_run_id_for_logging"
    config_path    = "config/api_sources.json"
  }
  
  annotations = ["config-driven", "api-ingestion", "rest-api"]

  activities_json = templatefile("${path.module}/pipeline_activities.json.tpl", {
    rest_dataset_name   = local.dataset_names.rest_source
    sink_dataset_name   = local.dataset_names.sink
    config_dataset_name = local.dataset_names.config
  })

  depends_on = [
    azurerm_data_factory_linked_custom_service.rest_source,
    azurerm_data_factory_linked_service_azure_blob_storage.adls_sink,
    azurerm_data_factory_custom_dataset.rest_source_dataset,
    azurerm_data_factory_custom_dataset.adls_sink_dataset,
    azurerm_data_factory_dataset_json.config_dataset
  ]
}

resource "azurerm_data_factory_custom_dataset" "rest_source_dataset" {
  name            = "RestResource1"
  data_factory_id = var.data_factory_id
  type            = "RestResource"

  linked_service {
    name = azurerm_data_factory_linked_custom_service.rest_source.name
    parameters = {
      "base_url" = "@dataset().base_url"
    }
  }

  parameters = {
    "base_url"     = "test",
    "relative_url" = "/"
  }

  type_properties_json = jsonencode({
    "relativeUrl" = "@dataset().relative_url"
  })
}

resource "azurerm_data_factory_dataset_json" "config_dataset" {
  name                = "ds_api_config_file"
  data_factory_id     = var.data_factory_id
  linked_service_name = azurerm_data_factory_linked_service_azure_blob_storage.adls_sink.name
  azure_blob_storage_location {
    container = var.storage_container_name
    path      = "config"
    filename  = "api_sources.json"
  }
  encoding = "UTF-8"
}

resource "azurerm_data_factory_custom_dataset" "adls_sink_dataset" {
  name            = "ds_adls_dynamic_sink"
  data_factory_id = var.data_factory_id
  type            = "Json"

  linked_service {
    name = azurerm_data_factory_linked_service_azure_blob_storage.adls_sink.name
  }

  parameters = {
    "FileName"   = "",
    "FolderPath" = ""
  }

  type_properties_json = <<JSON
  {
    "location": {
      "type": "AzureBlobStorageLocation",
      "fileName": "@dataset().FileName",
      "folderPath": "@dataset().FolderPath",
      "container": "raw"
    }
  }
  JSON
}
