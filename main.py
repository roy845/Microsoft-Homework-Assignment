from datetime import datetime, timedelta
from azure.mgmt.resource.resources.models import ResourceGroup
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage.models import StorageAccountCreateParameters
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.v2020_06_01.models import NetworkSecurityGroup
from azure.mgmt.network.models import NetworkSecurityGroup, SecurityRule, SecurityRuleProtocol,SecurityRuleAccess,SecurityRuleDirection
from azure.identity import AzureCliCredential
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient, generate_account_sas, ResourceTypes, AccountSasPermissions


def createResourceGroup(subscription_id,resource_group_name,location):
    print('Creating ResourceGroup ' + resource_group_name + '...')

    # Set the subscription ID and resource group name
    subscription_id = subscription_id
    resource_group_name = resource_group_name
    location = location

    # Create a ResourceManagementClient instance using AzureCliCredential
    credential = AzureCliCredential()
    resource_client = ResourceManagementClient(credential, subscription_id)

    # Create the resource group
    resource_group_params = ResourceGroup(location=location)
    resource_client.resource_groups.create_or_update(resource_group_name, resource_group_params)

    print('Finished Creating ResourceGroup' + resource_group_name + '...')

def createAccountStorage(subscription_id,resource_group_name,account_name,loc):

    print('Creating account storage'+account_name+'...')
    # Replace with your Azure subscription ID
    subscription_id = subscription_id

    # Replace with your Azure resource group and storage account names
    resource_group_name = resource_group_name
    account_name = account_name

    # Replace with the Azure region where you want to deploy the storage account
    location = loc

    # Create the Azure Storage account parameters
    account_params = StorageAccountCreateParameters(
        sku={"name": "Standard_LRS"},  # Replace with the desired SKU (e.g., Standard_LRS, Standard_GRS, etc.)
        kind="StorageV2",
        location=location
    )

    # Create the Azure Resource Manager and Storage clients
    credential = AzureCliCredential()
    resource_client = ResourceManagementClient(credential, subscription_id)
    storage_client = StorageManagementClient(credential, subscription_id)

    # Create the resource group if it doesn't exist
    resource_client.resource_groups.create_or_update(resource_group_name, {"location": location})

    # Create the Storage account
    storage_account = storage_client.storage_accounts.begin_create(resource_group_name, account_name, account_params).result()


    print(f"Storage account created with name '{storage_account.name}' and ID '{storage_account.id}'")


def createLinuxVm(subscription_id,resource_group_name,vname,subname,ipname,ipconfigname,nicname,vmname,username,password,loc):

    print(
        "Provisioning a virtual machine...some operations might take a \
    minute or two."
    )

    # Acquire a credential object using CLI-based authentication.
    credential = AzureCliCredential()



    # Step 1: Provision a resource group

    # Obtain the management object for resources, using the credentials
    # from the CLI login.
    resource_client = ResourceManagementClient(credential, subscription_id)

    # Constants we need in multiple places: the resource group name and
    # the region in which we provision resources. You can change these
    # values however you want.
    RESOURCE_GROUP_NAME = resource_group_name
    LOCATION = loc

    # Provision the resource group.
    rg_result = resource_client.resource_groups.create_or_update(
        RESOURCE_GROUP_NAME, {"location": LOCATION}
    )

    print(
        f"Provisioned resource group {rg_result.name} in the \
    {rg_result.location} region"
    )

    # For details on the previous code, see Example: Provision a resource
    # group at https://learn.microsoft.com/azure/developer/python/
    # azure-sdk-example-resource-group

    # Step 2: provision a virtual network

    # A virtual machine requires a network interface client (NIC). A NIC
    # requires a virtual network and subnet along with an IP address.
    # Therefore we must provision these downstream components first, then
    # provision the NIC, after which we can provision the VM.

    # Network and IP address names
    VNET_NAME = vname
    SUBNET_NAME = subname
    IP_NAME = ipname
    IP_CONFIG_NAME = ipconfigname
    NIC_NAME = nicname

    # Obtain the management object for networks
    network_client = NetworkManagementClient(credential, subscription_id)

    # Provision the virtual network and wait for completion
    poller = network_client.virtual_networks.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        VNET_NAME,
        {
            "location": LOCATION,
            "address_space": {"address_prefixes": ["10.0.0.0/16"]},
        },
    )

    vnet_result = poller.result()

    print(
        f"Provisioned virtual network {vnet_result.name} with address \
    prefixes {vnet_result.address_space.address_prefixes}"
    )

    # Step 3: Provision the subnet and wait for completion
    poller = network_client.subnets.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        VNET_NAME,
        SUBNET_NAME,
        {"address_prefix": "10.0.0.0/24"},
    )
    subnet_result = poller.result()

    print(
        f"Provisioned virtual subnet {subnet_result.name} with address \
    prefix {subnet_result.address_prefix}"
    )

    # Step 4: Provision an IP address and wait for completion
    poller = network_client.public_ip_addresses.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        IP_NAME,
        {
            "location": LOCATION,
            "sku": {"name": "Standard"},
            "public_ip_allocation_method": "Static",
            "public_ip_address_version": "IPV4",
        },
    )

    ip_address_result = poller.result()

    print(
        f"Provisioned public IP address {ip_address_result.name} \
    with address {ip_address_result.ip_address}"
    )

    # Step 5: Provision the network interface client
    poller = network_client.network_interfaces.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        NIC_NAME,
        {
            "location": LOCATION,
            "ip_configurations": [
                {
                    "name": IP_CONFIG_NAME,
                    "subnet": {"id": subnet_result.id},
                    "public_ip_address": {"id": ip_address_result.id},
                }
            ],
        },
    )

    nic_result = poller.result()

    print(f"Provisioned network interface client {nic_result.name}")

    # Step 6: Provision the virtual machine

    # Obtain the management object for virtual machines
    compute_client = ComputeManagementClient(credential, subscription_id)

    VM_NAME = vmname
    USERNAME = username
    PASSWORD = password

    print(
        f"Provisioning virtual machine {VM_NAME}; this operation might \
    take a few minutes."
    )

    # Provision the VM specifying only minimal arguments, which defaults
    # to an Ubuntu 18.04 VM on a Standard DS1 v2 plan with a public IP address
    # and a default virtual network/subnet.

    poller = compute_client.virtual_machines.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        VM_NAME,
        {
            "location": LOCATION,
            "storage_profile": {
                "image_reference": {
                    "publisher": "Canonical",
                    "offer": "UbuntuServer",
                    "sku": "16.04.0-LTS",
                    "version": "latest",
                }
            },
            "hardware_profile": {"vm_size": "Standard_DS1_v2"},
            "os_profile": {
                "computer_name": VM_NAME,
                "admin_username": USERNAME,
                "admin_password": PASSWORD,
            },
            "network_profile": {
                "network_interfaces": [
                    {
                        "id": nic_result.id,
                    }
                ]
            },
        },
    )

    vm_result = poller.result()

    print(f"Provisioned virtual machine {vm_result.name}")


def createWindowsVm(subscription_id, resource_group_name, vname, subname, ipname, ipconfigname, nicname, vmname, username, password, loc):

    print(
        "Provisioning a virtual machine...some operations might take a \
    minute or two."
    )

    # Acquire a credential object using CLI-based authentication.
    credential = AzureCliCredential()

    # Step 1: Provision a resource group

    # Obtain the management object for resources, using the credentials
    # from the CLI login.
    resource_client = ResourceManagementClient(credential, subscription_id)

    # Constants we need in multiple places: the resource group name and
    # the region in which we provision resources. You can change these
    # values however you want.
    RESOURCE_GROUP_NAME = resource_group_name
    LOCATION = loc

    # Provision the resource group.
    rg_result = resource_client.resource_groups.create_or_update(
        RESOURCE_GROUP_NAME, {"location": LOCATION}
    )

    print(
        f"Provisioned resource group {rg_result.name} in the \
    {rg_result.location} region"
    )

    # For details on the previous code, see Example: Provision a resource
    # group at https://learn.microsoft.com/azure/developer/python/
    # azure-sdk-example-resource-group

    # Step 2: provision a virtual network

    # A virtual machine requires a network interface client (NIC). A NIC
    # requires a virtual network and subnet along with an IP address.
    # Therefore we must provision these downstream components first, then
    # provision the NIC, after which we can provision the VM.

    # Network and IP address names
    VNET_NAME = vname
    SUBNET_NAME = subname
    IP_NAME = ipname
    IP_CONFIG_NAME = ipconfigname
    NIC_NAME = nicname

    # Obtain the management object for networks
    network_client = NetworkManagementClient(credential, subscription_id)

    # Provision the virtual network and wait for completion
    poller = network_client.virtual_networks.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        VNET_NAME,
        {
            "location": LOCATION,
            "address_space": {"address_prefixes": ["10.0.0.0/16"]},
        },
    )

    vnet_result = poller.result()

    print(
        f"Provisioned virtual network {vnet_result.name} with address \
    prefixes {vnet_result.address_space.address_prefixes}"
    )

    # Step 3: Provision the subnet and wait for completion
    poller = network_client.subnets.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        VNET_NAME,
        SUBNET_NAME,
        {"address_prefix": "10.0.0.0/24"},
    )
    subnet_result = poller.result()

    print(
        f"Provisioned virtual subnet {subnet_result.name} with address \
    prefix {subnet_result.address_prefix}"
    )

    # Step 4: Provision an IP address and wait for completion
    poller = network_client.public_ip_addresses.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        IP_NAME,
        {
            "location": LOCATION,
            "sku": {"name": "Standard"},
            "public_ip_allocation_method": "Static",
            "public_ip_address_version": "IPV4",
        },
    )

    ip_address_result = poller.result()

    print(
        f"Provisioned public IP address {ip_address_result.name} \
       with address {ip_address_result.ip_address}"
    )

    # Step 5: Provision the network interface client
    poller = network_client.network_interfaces.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        NIC_NAME,
        {
            "location": LOCATION,
            "ip_configurations": [
                {
                    "name": IP_CONFIG_NAME,
                    "subnet": {"id": subnet_result.id},
                    "public_ip_address": {"id": ip_address_result.id},
                }
            ],
        },
    )

    nic_result = poller.result()

    print(f"Provisioned network interface client {nic_result.name}")

    compute_client = ComputeManagementClient(credential, subscription_id)

    VM_NAME = vmname
    USERNAME = username
    PASSWORD = password

    print(
        f"Provisioning virtual machine {VM_NAME}; this operation might \
    take a few minutes."
    )

    # Provision the VM specifying only minimal arguments, which defaults
    # to an Ubuntu 18.04 VM on a Standard DS1 v2 plan with a public IP address
    # and a default virtual network/subnet.

    # Provision a Windows Server 2019 VM
    poller = compute_client.virtual_machines.begin_create_or_update(
        RESOURCE_GROUP_NAME,
        VM_NAME,
        {
            "location": LOCATION,
            "storage_profile": {
                "image_reference": {
                    "publisher": "MicrosoftWindowsServer",
                    "offer": "WindowsServer",
                    "sku": "2019-Datacenter",
                    "version": "latest",
                }
            },
            "hardware_profile": {"vm_size": "Standard_DS1_v2"},
            "os_profile": {
                "computer_name": VM_NAME,
                "admin_username": USERNAME,
                "admin_password": PASSWORD,
                "windows_configuration": {
                    "provision_vmagent": True,
                    "enable_automatic_updates": True
                }
            },
            "network_profile": {
                "network_interfaces": [
                    {
                        "id": nic_result.id,
                    }
                ]
            },
        },
    )

    vm_result = poller.result()

    print(f"Provisioned virtual machine {vm_result.name}")

def setNSG(subscription_id,resource_group_name,nsg_name,loc):

    print("Setting Network Security Group...")

    # Replace the values with your own
    subscription_id = subscription_id
    resource_group_name = resource_group_name
    nsg_name = nsg_name

    # Create the Azure CLI credential
    credential = AzureCliCredential()
    network_client = NetworkManagementClient(credential, subscription_id)

    # Create the NSG
    nsg = NetworkSecurityGroup(location=loc)
    nsg_result = network_client.network_security_groups.begin_create_or_update(
        resource_group_name,
        nsg_name,
        nsg
    )

    print("Finished Setting Network Security Group!")


def associateNsgWithNic(subscription_id,resource_group_name,nsg_name,nic_name):
    print("Associating Network Security Group with server nic...")

    # Replace the values with your own
    subscription_id = subscription_id
    resource_group_name = resource_group_name
    nsg_name = nsg_name
    nic_name = nic_name

    # Create the Azure CLI credential
    credential = AzureCliCredential()
    network_client = NetworkManagementClient(credential, subscription_id)

    # Get the NSG
    nsg = network_client.network_security_groups.get(resource_group_name, nsg_name)

    # Get the NIC
    nic = network_client.network_interfaces.get(resource_group_name, nic_name)

    # Associate the NSG with the NIC
    nic.network_security_group = nsg
    nic_result = network_client.network_interfaces.begin_create_or_update(resource_group_name, nic_name, nic)

    print("Finished Associating Network Security Group with server nic!")


def setPort3389(subscription_id,resource_group_name,nsg_name):

    print("Setting Port 3389 for remote connection...")

    # Set subscription ID, resource group name, and NSG name
    subscription_id = subscription_id
    resource_group_name = resource_group_name
    nsg_name = nsg_name

    # Create a NetworkManagementClient instance using AzureCliCredential
    credential = AzureCliCredential()
    network_client = NetworkManagementClient(credential, subscription_id)

    # Get the NSG
    nsg = network_client.network_security_groups.get(resource_group_name, nsg_name)

    # Get the existing NSG object
    nsg = network_client.network_security_groups.get(resource_group_name, nsg_name)

    # Create the new security rule object
    new_rule = SecurityRule(
        name="RDP",
        description="Allow RDP traffic on port 3389",
        protocol=SecurityRuleProtocol.tcp,
        source_address_prefix="*",
        source_port_range="*",
        destination_address_prefix="*",
        destination_port_range="3389",
        access=SecurityRuleAccess.allow,
        direction=SecurityRuleDirection.inbound,
        priority=1010  # Make sure this priority value is higher than any existing rules
    )

    # Add the new security rule to the NSG
    nsg.security_rules.append(new_rule)

    # Update the NSG on Azure
    network_client.network_security_groups.begin_create_or_update(resource_group_name, nsg_name, nsg)

    print("Finished Setting Port 3389 for remote connection!")

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
#createResourceGroup(subscription_id,resource_group_name,location)
#createAccountStorage(subscription_id,resource_group_name,account_name,loc)
#createLinuxVm(subscription_id,resource_group_name,vname,subname,ipname,ipconfigname,nicname,vmname,username,password,loc)
#createWindowsVm(subscription_id, resource_group_name, vname, subname, ipname, ipconfigname, nicname, vmname, username, password, loc)
#setNSG(subscription_id,resource_group_name,nsg_name,loc)
#associateNsgWithNic(subscription_id,resource_group_name,nsg_name,nic_name)
#setPort3389(subscription_id,resource_group_name,nsg_name)



