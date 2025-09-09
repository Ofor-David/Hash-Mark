output "resource_group_name" {
  description = "The resource group"
  value       = azurerm_resource_group.rg.name
}
output "resource_group_location" {
  description = "The resource group"
  value       = azurerm_resource_group.rg.location
}

output "resource_group_id" {
  description = "The resource group ID"
  value       = azurerm_resource_group.rg.id
}
output "storage_account_primary_connection_string"{
    description = "The primary connection string for the storage account"
    value       = azurerm_storage_account.storage.primary_connection_string
}

output "table_name"{
    description = "The name of the table"
    value       = azurerm_storage_table.table.name
}

output "main_storage_account_id"{
  value = azurerm_storage_account.storage.id
}