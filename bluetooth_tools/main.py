import asyncio
from bleak import BleakScanner, BleakClient

async def read_characteristic(device_address, characteristic_uuid):
    async with BleakClient(device_address) as client:
        print(f"Connected: {client.is_connected}")

        # Reading the characteristic value
        value = await client.read_gatt_char(characteristic_uuid)
        print(f"Value: {value}")

async def scan_for_devices():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    if not devices:
        print("No devices found.")
    else:
        for device in devices:
            print(f"Device: {device.name}, Address: {device.address}")

    await read_characteristic("80:E1:27:F0:D3:AD", "00005001-0000-1000-8000-00805F9B34FB")

async def discover_services_and_characteristics(device_address):
    async with BleakClient(device_address) as client:
        print(f"Connected: {client.is_connected}")

        # Discover services and characteristics
        services = await client.get_services()

        for service in services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")

        await read_characteristic(device_address, "00000501-0000-1000-8000-00805f9b34fb")

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(discover_services_and_characteristics("80:E1:27:F0:D3:AD"))
