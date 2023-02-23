from datetime import datetime, timedelta
from azure.identity import AzureCliCredential
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient, generate_account_sas, ResourceTypes, AccountSasPermissions

def getStorageAccountNames(subscription_id,resource_group_name):
    storage_accounts_names = []
    # Create an AzureCliCredential object to authenticate with Azure
    credential = AzureCliCredential()

    # Create a StorageManagementClient object using the AzureCliCredential object
    storage_mgmt_client = StorageManagementClient(credential, subscription_id)

    # Get the list of storage accounts associated with the current Azure credentials
    storage_accounts = storage_mgmt_client.storage_accounts.list_by_resource_group(resource_group_name)

    # Iterate over the storage accounts and print their names
    for account in storage_accounts:
        storage_accounts_names.append(account.name)

    return storage_accounts_names


def renewConnectionStrings(subscription_id,resource_group_name,storage_account_name):
    # Create the Azure Resource Manager and Storage clients
    credential = AzureCliCredential()

    storage_client = StorageManagementClient(credential, subscription_id)
    keys = storage_client.storage_accounts.list_keys(resource_group_name, storage_account_name)
    sas_token = generate_account_sas(
        account_name=storage_account_name,
        account_key=keys.keys[0].value,
        resource_types=ResourceTypes(service=True, container=True, object=True),
        permission=AccountSasPermissions(read=True, write=True, delete=True, list=True, add=True, create=True,
                                         update=True, process=True, immutablestorage=True, permanentdelete=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )

    connection_string = f'BlobEndpoint=https://{storage_account_name}.blob.core.windows.net/;QueueEndpoint=https://{storage_account_name}.queue.core.windows.net/;FileEndpoint=https://{storage_account_name}.file.core.windows.net/;TableEndpoint=https://{storage_account_name}.table.core.windows.net/;SharedAccessSignature={sas_token}'
    return connection_string




def copy_blobs(source_connection_string, dest_connection_string, src_container_name, dst_container_name, number_of_blobs):
    print('Start creating, uploading, and copying ' + str(number_of_blobs) + ' blobs...')

    # Enter your source and destination storage account connection strings
    source_connection_string = source_connection_string
    destination_connection_string = dest_connection_string

    # Create a BlobServiceClient object for each storage account
    source_blob_service_client = BlobServiceClient.from_connection_string(source_connection_string)
    destination_blob_service_client = BlobServiceClient.from_connection_string(destination_connection_string)

    # Create a container in the source storage account
    source_container_name = src_container_name
    source_blob_service_client.create_container(source_container_name)

    # Upload 100 blobs to the source container
    for i in range(1, number_of_blobs+1):
        source_blob_name = "blob" + str(i)
        source_blob_data = b"Hello, World!"
        source_blob_client = source_blob_service_client.get_blob_client(container=source_container_name,
                                                                        blob=source_blob_name)
        source_blob_client.upload_blob(source_blob_data)

    # Create a container in the destination storage account
    destination_container_name = dst_container_name
    destination_blob_service_client.create_container(destination_container_name)

    # Copy the 100 blobs from the source container to the destination container
    for i in range(1, number_of_blobs+1):
        source_blob_name = "blob" + str(i)
        destination_blob_name = "copy_blob" + str(i)
        source_blob_url = source_blob_service_client.get_blob_client(container=source_container_name,
                                                                     blob=source_blob_name).url
        destination_blob_client = destination_blob_service_client.get_blob_client(container=destination_container_name,
                                                                                  blob=destination_blob_name)
        destination_blob_client.start_copy_from_url(source_blob_url)


    print('Finished copying ' + str(number_of_blobs) + ' blobs!')



#function calls
#source_storage_account,dest_storage_account = getStorageAccountNames(subscription_id,resource_group_name)
#source_connection_string = renewConnectionStrings(subscription_id, resource_group_name, source_storage_account)
#dest_connetion_string  = renewConnectionStrings(subscription_id, resource_group_name, dest_storage_account)
#copy_blobs(source_connection_string, dest_connection_string, src_container_name, dst_container_name,number_of_blobs)


