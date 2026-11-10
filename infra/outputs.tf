
output "api_url" {
  description = "Public URL of the deployed ticketing API."
  value       = "https://${azurerm_linux_web_app.ticketing.default_hostname}"
}

