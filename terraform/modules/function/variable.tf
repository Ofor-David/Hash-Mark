variable "function_storage_account_name"{
    type = string
    description = "The name of the storage account to use for the function app"
}

variable "resource_group_name"{
    type = string
    description = "The name of the resource group to deploy all resources"

}

variable "name_prefix"{
    type = string
    description = "Name prefix for all your resources"
}

variable "resource_group_location"{
    type = string
    description = "The location of the resource group to deploy all resources"
}
variable "storage_account_primary_connection_string"{
    type = string
    description = "The primary connection string for the storage account"
}

variable "table_name"{
    type = string
    description = "The name of the table"
}

variable "main_storage_account_id"{
    type = string
    description = "The main storage account id"
}