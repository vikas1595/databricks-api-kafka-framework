# terraform/modules/adf_api_ingestion_pipeline/variables.tf

variable "data_factory_id" {
  description = "The ID of the Azure Data Factory where resources will be created."
  type        = string
}

variable "storage_container_name" {
  description = "The name of the storage container."
  type        = string
}

variable "storage_connection_string" {
  description = "The primary connection string for the Azure Storage Account."
  type        = string
  sensitive   = true
}