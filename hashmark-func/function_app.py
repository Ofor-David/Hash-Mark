import azure.functions as func
import logging
import hashlib
from datetime import datetime
from azure.data.tables import TableServiceClient
import os

app = func.FunctionApp()


@app.blob_trigger(
    arg_name="myblob", path="uploads/{name}", connection="AzureWebJobsStorage"
)
def main(myblob: func.InputStream):
    logging.info(
        f"Python blob trigger function processed blob"
        f"Name: {myblob.name}\n"
        f"Blob Size: {myblob.length} bytes"
    )

    # Read blob content
    file_bytes = myblob.read()

    # Compute SHA-256 hash
    sha256hash = hashlib.sha256(file_bytes).hexdigest()
    sha3hash = hashlib.sha3_256(file_bytes).hexdigest()
    hashes = {
        "sha256": sha256hash,
        "sha3": sha3hash
    }
    
    file_info = {"name": myblob.name, "size": myblob.length}
    
    store_hash_record(file_info, hashes)


# Store the hash in a table
def store_hash_record(file_info, hashes):
    try:
        connection_string = os.environ["AzureWebJobsStorage"]
        table_service = TableServiceClient.from_connection_string(
            conn_str=connection_string
        )
        table_name = os.environ["TABLE_NAME"]
        table_client = table_service.get_table_client(table_name=table_name)

        entity = {
            # PartitionKey: Groups related records together (improves query performance)
            # Using date allows us to easily query records by day/month
            "PartitionKey": datetime.now().strftime("%Y-%m-%d"),
            # RowKey: Must be unique within the partition
            # Using timestamp + hash snippet ensures uniqueness
            "RowKey": f"{int(datetime.now().timestamp())}_{hashes['sha256'][:8]}",
            
            "original_filename": file_info["name"],
            "file_size": file_info["size"],
            "sha256_hash": hashes["sha256"],
            "sha3_hash": hashes["sha3"],
            "upload_timestamp": datetime.now().isoformat(),
            "hash_algorithm_version": "1.0",
            "verification_count": 0,
            "status": "verified",
        }

        table_client.create_entity(entity=entity)
        logging.info("Hash record stored successfully.")
    except Exception as e:
        logging.error(f"Error storing hash record: {e}")
