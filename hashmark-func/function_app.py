from re import search
import azure.functions as func
import logging
import hashlib
from datetime import datetime
from azure.data.tables import TableServiceClient
from azure.storage.blob import BlobServiceClient
import os
import json
from requests_toolbelt.multipart import decoder


app = func.FunctionApp()

# Upload blob trigger function
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
    hashes = {"sha256": sha256hash, "sha3": sha3hash}

    file_info = {"name": myblob.name, "size": myblob.length}
    # Check if hash already exists in table
    if search_hash_in_table(sha256hash).get("exists"):
        logging.info(f"Hash {sha256hash} already exists in table. Deleting blob {myblob.name}.")
        delete_source_blob(myblob.name.split("/")[-1])
        return
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
        file_name = file_info["name"].split("/")[-1]

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
            "auto_deleted": True, # Indicates if the original blob was auto-deleted after hashing
        }
        logging.info(f"file name to be deleted is {file_name}")

        table_client.create_entity(entity=entity)
        delete_source_blob(file_name)
        logging.info("Hash record stored successfully.")
    except Exception as e:
        logging.error(f"Error storing hash record: {e}")

def delete_source_blob(blob_name: str):
    try:
        connection_string = os.environ["AzureWebJobsStorage"]

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "uploads"  # Ensure this matches your blob trigger path
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

        blob_client.delete_blob()
        logging.info(f"Source blob '{blob_name}' deleted successfully.")
    except Exception as e:
        logging.error(f"Error deleting source blob '{blob_name}': {e}")

# HTTP trigger function for verification
@app.route(route="verify", methods=["POST"])
def verify_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP API endpoint for verifying if a file existed at a certain time.

    Accepts two types of requests:
    1. File upload (multipart/form-data) - we'll hash it and check
    2. JSON with hash string - we'll check the hash directly

    Why HTTP trigger instead of blob trigger:
    - Users need to actively request verification
    - We need to return results immediately to the user
    - Supports both web interfaces and API integrations
    """

    try:
        logging.info("Verification request received")

        # Determine request type based on content
        content_type = req.headers.get("content-type", "")

        if content_type.startswith("multipart/form-data"):
            # Handle file upload verification
            return handle_file_verification(req)
        elif content_type.startswith("application/json"):
            # Handle hash-only verification
            return handle_hash_verification(req)
        else:
            # Unsupported content type
            return func.HttpResponse(
                json.dumps(
                    {
                        "success": False,
                        "error": "Unsupported content type. Use multipart/form-data for files or application/json for hash strings.",
                        "supported_types": ["multipart/form-data", "application/json"],
                    }
                ),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

    except Exception as e:
        logging.error(f"Error in verification endpoint: {str(e)}")
        return func.HttpResponse(
            json.dumps(
                {
                    "success": False,
                    "error": "Internal server error occurred during verification",
                }
            ),
            status_code=500,
            headers={"Content-Type": "application/json"},
        )

def handle_file_verification(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Get raw body (bytes)
        body = req.get_body()
        content_type = req.headers.get("Content-Type")

        # Decode multipart data
        multipart_data = decoder.MultipartDecoder(body, content_type)

        response_lines = []
        for part in multipart_data.parts:
            # Each part has headers and content
            content_disposition = part.headers.get(b"Content-Disposition", b"").decode()

            if b"filename=" in part.headers.get(b"Content-Disposition", b""):
                # It's a file
                filename = content_disposition.split("filename=")[-1].strip('"')
                logging.info(f"Processing uploaded file: {filename}")
                file_hash = hashlib.sha256(part.content).hexdigest()
                verification_result = search_hash_in_table(file_hash)
                
                # Build response
                response_data = {
                    "success": True,
                    "verification": verification_result,
                    "request_info": {
                        "provided_hash": file_hash,
                        "verification_timestamp": datetime.now().isoformat(),
                    },
                }

                return func.HttpResponse(
                    json.dumps(response_data, indent=2),
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                )

                
            """
            else:
                # It's a normal form field
                value = part.text  # decode text
                name = content_disposition.split("name=")[-1].strip('"')
                response_lines.append(f"Field {name} = {value}")
 """
        return func.HttpResponse("\n".join(response_lines))

    except Exception as e:
        return func.HttpResponse(f"Error: {str(e)}", status_code=400)


def handle_hash_verification(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle verification when user provides a hash string.

    This is useful when:
    1. User already knows the hash
    2. Integrating with other systems
    3. File is too large to upload again
    """

    try:
        logging.info("Processing hash-only verification request")
        # Parse JSON request body
        req_body = req.get_json()

        if not req_body or "hash" not in req_body:
            return func.HttpResponse(
                json.dumps(
                    {
                        "success": False,
                        "error": "Missing 'hash' field in JSON request body",
                        "example": {"hash": "abc123..."},
                    }
                ),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

        hash_value = req_body["hash"]

        # Validate hash format (SHA-256 should be 64 hex characters)
        # Why validate: Prevents unnecessary database queries for invalid hashes
        if not isinstance(hash_value, str) or len(hash_value) != 64:
            return func.HttpResponse(
                json.dumps(
                    {
                        "success": False,
                        "error": "Invalid hash format. SHA-256 hashes should be 64 hexadecimal characters.",
                        "received_length": (
                            len(hash_value) if isinstance(hash_value, str) else 0
                        ),
                    }
                ),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

        logging.info(f"Verifying hash: {hash_value}")

        # Search for the hash in our table
        verification_result = search_hash_in_table(hash_value)

        # Build response
        response_data = {
            "success": True,
            "verification": verification_result,
            "request_info": {
                "provided_hash": hash_value,
                "verification_timestamp": datetime.now().isoformat(),
            },
        }

        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    except Exception as e:
        logging.error(f"Error handling hash verification: {str(e)}")
        return func.HttpResponse(
            json.dumps(
                {
                    "success": False,
                    "error": f"Failed to process hash verification: {str(e)}",
                }
            ),
            status_code=500,
            headers={"Content-Type": "application/json"},
        )


def search_hash_in_table(hash_value: str) -> dict:
    """
    Search for a specific hash in our Azure Table Storage.

    Returns detailed information about the file if found.

    Args:
        hash_value: The SHA-256 hash to search for

    Returns:
        dict: Verification results with file details or not-found info
    """

    try:
        # Connect to table storage
        connection_string = os.environ.get("AzureWebJobsStorage")
        table_name = os.environ.get("TABLE_NAME")

        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client(table_name)

        # Search for entities with matching hash
        # Why filter query: More efficient than downloading all records
        filter_query = f"sha256_hash eq '{hash_value}'"

        entities = list(table_client.query_entities(filter_query))

        if not entities:
            # Hash not found in our records
            return {
                "exists": False,
                "message": "This file hash was not found in our records.",
                "searched_hash": hash_value,
                "search_timestamp": datetime.now().isoformat(),
            }

        # File found! Get the first (and should be only) match
        entity = entities[0]

        # Update verification count
        # Why track this: Analytics on how often files are verified
        entity["verification_count"] = int(entity.get("verification_count", 0)) + 1
        entity["last_verified"] = datetime.now().isoformat()

        try:
            # Update the entity with new verification count
            table_client.update_entity(entity, mode="replace")
        except:
            # Don't fail verification if we can't update count
            logging.warning("Failed to update verification count")

        # Return detailed verification results
        return {
            "exists": True,
            "message": "File verified successfully! This file existed in our system.",
            "file_details": {
                "original_filename": entity.get("original_filename"),
                "file_size": entity.get("file_size"),
                "upload_timestamp": entity.get("upload_timestamp"),
                "sha256_hash": entity.get("sha256_hash"),
                "verification_count": entity.get("verification_count", 1),
                "last_verified": entity.get("last_verified"),
            },
            "proof_details": {
                "partition_key": entity.get("PartitionKey"),
                "row_key": entity.get("RowKey"),
                "storage_status": entity.get("status", "verified"),
            },
        }

    except Exception as e:
        logging.error(f"Error searching hash in table: {str(e)}")
        return {
            "exists": False,
            "error": True,
            "message": "Error occurred while searching for file hash",
            "details": str(e),
        }
