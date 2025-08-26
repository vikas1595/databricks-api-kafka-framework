# terraform/main.tf

# --- Data Sources to look up existing infrastructure ---

data "azurerm_resource_group" "rg" {
  name = var.resource_group_name
}

data "azurerm_data_factory" "adf" {
  name                = var.data_factory_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_storage_account" "adls" {
  name                = var.storage_account_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

# --- Resources to Create/Manage ---

# CORRECTED: Add this resource to ensure the container exists.
# This will create the container if it's not there, or just adopt it if it already exists.
resource "azurerm_storage_container" "main" {
  name                  = var.storage_container_name
  storage_account_name  = data.azurerm_storage_account.adls.name
  container_access_type = "private"
}

# This resource now implicitly depends on the container existing.
resource "azurerm_storage_blob" "api_config" {
  name                   = "config/api_sources.json"
  storage_account_name   = data.azurerm_storage_account.adls.name
  storage_container_name = azurerm_storage_container.main.name # Reference the resource directly
  type                   = "Block"
  source                 = "../adf/api_sources.json"
}

# --- Call the ADF Pipeline Module ---

module "api_ingestion_pipeline" {
  source = "./modules/adf_api_ingestion_pipeline"

  data_factory_id              = data.azurerm_data_factory.adf.id
  storage_container_name       = azurerm_storage_container.main.name # Pass the container name from the resource
  storage_connection_string    = data.azurerm_storage_account.adls.primary_connection_string
  
  depends_on = [
    azurerm_storage_blob.api_config
  ]
}

