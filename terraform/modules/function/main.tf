# 1. Storage Account for Function (required by Azure Functions)
# Functions need their own storage account for runtime state.
resource "azurerm_storage_account" "function_storage" {
  name                     = var.function_storage_account_name   # must be unique
  resource_group_name      = var.resource_group_name
  location                 = var.resource_group_location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 2. App Service Plan (Consumption = serverless pricing)
resource "azurerm_service_plan" "function_plan" {
  name                = "func-plan"
  resource_group_name = var.resource_group_name
  location            = var.resource_group_location
  os_type             = "Linux"
  sku_name            = "Y1"   # Y1 = consumption plan (pay-per-execution)
}

# 3. Function App
resource "azurerm_linux_function_app" "proof_function" {
  name                       = "${var.name_prefix}-hash-function"
  resource_group_name        = var.resource_group_name
  location                   = var.resource_group_location
  service_plan_id            = azurerm_service_plan.function_plan.id
  storage_account_name       = azurerm_storage_account.function_storage.name
  storage_account_access_key = azurerm_storage_account.function_storage.primary_access_key

  site_config {
    application_stack {
      python_version = "3.9"   # we’ll use Python for the function
    }
  }

  app_settings = {
    "AzureWebJobsStorage" = var.storage_account_primary_connection_string
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "TABLE" = var.table_name
  }
}
