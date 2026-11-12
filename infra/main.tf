
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Group related Azure resources.
resource "azurerm_resource_group" "ticketing" {
  name     = var.resource_group_name
  location = var.location
}

# Provide Linux compute resources for the API.
resource "azurerm_service_plan" "ticketing" {
  name                = "${var.app_name}-plan"
  location            = azurerm_resource_group.ticketing.location
  resource_group_name = azurerm_resource_group.ticketing.name

  os_type  = "Linux"
  sku_name = "B1"
}

# Define the web app that would host the FastAPI server.
resource "azurerm_linux_web_app" "ticketing" {
  name                = var.app_name
  location            = azurerm_resource_group.ticketing.location
  resource_group_name = azurerm_resource_group.ticketing.name
  service_plan_id     = azurerm_service_plan.ticketing.id
  https_only          = true

  site_config {
    app_command_line = "python -m uvicorn ticketing_system.api.main:app --app-dir src --host 0.0.0.0 --port 8000"

    application_stack {
      python_version = "3.13"
    }
  }
}

