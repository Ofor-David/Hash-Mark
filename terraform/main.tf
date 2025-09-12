module "storage"{
    source = "./modules/storage"
    name_prefix = var.name_prefix
    region = var.region
    storage_account_name = var.storage_account_name
}

module "function"{
    source = "./modules/function"
    resource_group_name = module.storage.resource_group_name
    resource_group_location = module.storage.resource_group_location
    function_storage_account_name = "${var.name_prefix}funcstorage"
    storage_account_primary_connection_string = module.storage.storage_account_primary_connection_string
    table_name = module.storage.table_name
    name_prefix = var.name_prefix
    main_storage_account_id = module.storage.main_storage_account_id
}

module "sp"{
    source = "./modules/service_principal"
    resource_group_id = module.storage.resource_group_id
    subscription_id = var.subscription_id
}

output "gh_actions_sp_credentials" {
  value = module.sp.gh_actions_sp_credentials
  sensitive = true
}
output "AzureWebJobsStorage"{
    value = module.storage.storage_account_primary_connection_string
    sensitive = true
}