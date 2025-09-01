module "storage"{
    source = "./modules/storage"
    name_prefix = var.name_prefix
    region = var.region
    storage_account_name = var.storage_account_name
}