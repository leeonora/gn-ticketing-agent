
variable "resource_group_name" {
  description = "Name of the Azure resource group."
  type        = string
  default     = "gn-ticketing-rg"
}

variable "location" {
  description = "Azure region where resources will be created."
  type        = string
  default     = "westeurope"
}

variable "app_name" {
  description = "Name of the Azure Web App."
  type        = string
  default     = "gn-ticketing-api-demo"
}

