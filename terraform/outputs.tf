# terraform/outputs.tf

output "pipeline_name" {
  description = "The name of the deployed ADF ingestion pipeline."
  value       = module.api_ingestion_pipeline.pipeline_name
}