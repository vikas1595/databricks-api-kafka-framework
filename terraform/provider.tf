terraform {
  required_version = ">= 1.5.0, <= 1.5.7"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.42.0"
    }
  }
}

provider "azurerm" {
  resource_provider_registrations = "none" # something when local running?
  subscription_id = var.subscription_id
  features {}
}
