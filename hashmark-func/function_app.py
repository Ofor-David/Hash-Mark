import azure.functions as func
import logging
import hashlib

app = func.FunctionApp()

@app.blob_trigger(arg_name="myblob", path="uploads/{name}",connection="AzureWebJobsStorage") 
def main(myblob: func.InputStream):
     logging.info(f"Python blob trigger function processed blob"
                 f"Name: {myblob.name}\n"
                 f"Blob Size: {myblob.length} bytes")
     
     # Read blob content
     file_bytes = myblob.read()
     
     # Compute SHA-256 hash
     file_hash = hashlib.sha256(file_bytes).hexdigest()
     
     logging.info(f"SHA-256 Hash: {file_hash}")


# Store the hash in a table