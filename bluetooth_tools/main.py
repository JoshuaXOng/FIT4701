import asyncio
import argparse
from bleak import BleakScanner, BleakClient

def main():
    root_parser = argparse.ArgumentParser()
    def root_command(program_arguments):
        root_parser.print_help()
    root_parser.set_defaults(command=root_command)

    root_subparsers = root_parser.add_subparsers(title="subcommands")

    scan_parser = root_subparsers.add_parser("scan")
    def scan_command(program_arguments):
        asyncio.get_event_loop().run_until_complete(scan_devices())
    scan_parser.set_defaults(command=scan_command)

    info_parser = root_subparsers.add_parser("info")
    info_parser.add_argument("--mac")
    info_parser.add_argument("--characteristic")
    def info_command(program_arguments):
        asyncio.get_event_loop().run_until_complete(
            device_information(program_arguments.mac)
        )
        if program_arguments.characteristic:
            asyncio.get_event_loop().run_until_complete(
                read_characteristic(
                    program_arguments.mac,
                    program_arguments.characteristic
                )
            )

    info_parser.set_defaults(command=info_command)

    program_arguments = root_parser.parse_args()
    program_arguments.command(program_arguments)

async def scan_devices():
    devices = await BleakScanner.discover()
    for device in devices:
        print(f"Device: {device.name}, Address: {device.address}")

async def device_information(device_address):
    async with BleakClient(device_address) as client:
        for service in client.services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid}")

async def read_characteristic(device_address, characteristic_uuid):
    async with BleakClient(device_address) as client:
        value = await client.read_gatt_char(characteristic_uuid)
        print(f"Value: {value}")

if __name__ == "__main__":
    main()
