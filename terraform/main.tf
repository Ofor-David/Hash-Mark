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
}