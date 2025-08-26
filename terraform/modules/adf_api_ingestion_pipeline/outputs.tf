# terraform/outputs.tf

output "pipeline_name" {
  description = "The name of the deployed ADF ingestion pipeline."
  value       = "test"
  # azurerm_data_factory_pipeline.ingestion_pipeline.name
}