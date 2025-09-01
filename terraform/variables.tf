variable "name_prefix"{
    type = string
    description = "Name prefix for all your resources"
}
variable "region"{
    type = string
    description = "location to deploy all resources"
}

variable "storage_account_name"{
    type = string
    description = "unique name for the storage account"
}

variable "subscription_id"{
    type = string
    description = "The subscription ID to deploy resources into"
}