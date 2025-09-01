# 1. Resource Group
resource "azurerm_resource_group" "rg" {
  name     = "${var.name_prefix}-rg"
  location = var.region
}

# 2. Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name   # must be globally unique, lowercase only
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 3. Blob Container
resource "azurerm_storage_container" "container" {
  name                  = "uploads"
  storage_account_name = azurerm_storage_account.storage.name
  container_access_type = "private"
}

# 4. Table Storage
resource "azurerm_storage_table" "table" {
  name                 = "${var.name_prefix}Records"
  storage_account_name = azurerm_storage_account.storage.name
}