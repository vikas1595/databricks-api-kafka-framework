# terraform/variables.tf

variable "resource_group_name" {
  description = "The name of the existing Azure Resource Group."
  type        = string
}

variable "location" {
  description = "The Azure region where the existing resources are located."
  type        = string
}

variable "data_factory_name" {
  description = "The name of the existing Azure Data Factory."
  type        = string
}

variable "storage_account_name" {
  description = "The name of the existing Azure Data Lake Storage account."
  type        = string
}

variable "storage_container_name" {
  description = "The name of the container to store the config file and raw data."
  type        = string
  default     = "raw"
}
variable "subscription_id" {
  description = "The subscription ID where the resources are located."
  type        = string
  
}