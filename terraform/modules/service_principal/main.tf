# Service Principal app registration
resource "azuread_application" "gh_actions_app" {
  display_name = "gh-actions-hashmark"
}

resource "azuread_service_principal" "gh_actions_sp" {
  client_id = azuread_application.gh_actions_app.client_id
}

resource "azuread_service_principal_password" "gh_actions_secret" {
  service_principal_id = azuread_service_principal.gh_actions_sp.id
}

# Assign Contributor role to SP on your Function App Resource Group
resource "azurerm_role_assignment" "gh_actions_contributor" {
  scope                = var.resource_group_id
  role_definition_name = "Contributor"
  principal_id         = azuread_service_principal.gh_actions_sp.object_id
}

data "azurerm_client_config" "current" {}

