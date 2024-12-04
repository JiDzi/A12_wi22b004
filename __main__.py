"""Ein Pulumi-Skript zur Erstellung einer Azure-VM mit Monitoring"""

import pulumi
from pulumi_azure_native import resources, storage, network, compute, insights

# Konfigurationsvariablen
resource_group_name = "A12_Monitoring"
location = "westeurope"
vm_name = "monitored-linux-vm"
size = "Standard_B1s"
admin_username = "azureuser"
admin_password = "Password1234!"

# Resource Group erstellen
resource_group = resources.ResourceGroup(resource_group_name, location=location)

# Speicherkonto für Boot-Diagnose erstellen
storage_account = storage.StorageAccount(
    "sa",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    sku={"name": storage.SkuName.STANDARD_LRS},
    kind=storage.Kind.STORAGE_V2,
)

# Virtuelles Netzwerk erstellen
vnet = network.VirtualNetwork(
    "vnet",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    address_space=network.AddressSpaceArgs(address_prefixes=["10.0.0.0/16"]),
)

# Subnetz erstellen
subnet = network.Subnet(
    "subnet",
    resource_group_name=resource_group.name,
    virtual_network_name=vnet.name,
    address_prefix="10.0.1.0/24",
)

# Netzwerkschnittstelle (NIC) erstellen
nic = network.NetworkInterface(
    "nic",
    resource_group_name=resource_group.name,
    location=resource_group.location,
    ip_configurations=[
        network.NetworkInterfaceIPConfigurationArgs(
            name="ipconfig",
            subnet=network.SubnetArgs(id=subnet.id),
            private_ip_allocation_method="Dynamic",
        )
    ],
)

# Virtuelle Maschine mit Boot-Diagnose erstellen
vm = compute.VirtualMachine(
    vm_name,
    resource_group_name=resource_group.name,
    location=resource_group.location,
    hardware_profile=compute.HardwareProfileArgs(vm_size=size),
    os_profile=compute.OSProfileArgs(
        admin_username=admin_username,
        admin_password=admin_password,
        computer_name=vm_name,
    ),
    storage_profile=compute.StorageProfileArgs(
        os_disk=compute.OSDiskArgs(
            create_option="FromImage",
            managed_disk=compute.ManagedDiskParametersArgs(
                storage_account_type="Standard_LRS",
            ),
        ),
        image_reference=compute.ImageReferenceArgs(
            publisher="Canonical",
            offer="UbuntuServer",
            sku="18.04-LTS",
            version="latest",
        ),
    ),
    network_profile=compute.NetworkProfileArgs(
        network_interfaces=[
            compute.NetworkInterfaceReferenceArgs(id=nic.id),
        ]
    ),
    diagnostics_profile=compute.DiagnosticsProfileArgs(
        boot_diagnostics=compute.BootDiagnosticsArgs(
            enabled=True,
            storage_uri=storage_account.primary_endpoints.blob,
        )
    ),
)

# Metric Alert für CPU-Auslastung hinzufügen
alert_rule = insights.MetricAlert(
    "vmCpuUsageAlert",
    resource_group_name=resource_group.name,
    location="global",  # Globale Alert-Regel erforderlich
    severity=3,
    window_size="PT30M",  # 30-Minuten Intervall
    evaluation_frequency="PT1M",  # Evaluierung alle Minute
    enabled=True,
    scopes=[vm.id],
    criteria=insights.MetricAlertSingleResourceMultipleMetricCriteriaArgs(
        odata_type="Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria",  # Globale Kriterien
        all_of=[
            insights.MetricCriteriaArgs(
                name="HighCpuUsage",
                metric_namespace="Microsoft.Compute/virtualMachines",  # Namespace für VM-Metriken
                metric_name="Percentage CPU",  # CPU-Auslastung
                operator="GreaterThan",  # Schwellenwert-Regel
                threshold=80,  # 80% CPU-Nutzung
                time_aggregation="Maximum",  # Maximalwert
                criterion_type="StaticThresholdCriterion",  # Statische Schwelle
            )
        ],
    ),
    auto_mitigate=True,
    description="Alert rule for CPU usage above 80% on monitored Linux VM.",
)

# Outputs
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("vnet_name", vnet.name)
pulumi.export("subnet_name", subnet.name)
pulumi.export("vm_name", vm.name)
