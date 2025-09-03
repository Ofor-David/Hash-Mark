# Output JSON for GitHub Secrets
output "gh_actions_sp_credentials" {
  value = jsonencode({
    clientId       = azuread_application.gh_actions_app.client_id
    clientSecret   = azuread_service_principal_password.gh_actions_secret.value
    subscriptionId = var.subscription_id
    tenantId       = data.azurerm_client_config.current.tenant_id
  })
  sensitive = true
}