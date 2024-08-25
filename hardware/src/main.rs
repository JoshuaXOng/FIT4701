#![no_std]
#![no_main]

mod adapter;

use core::time::Duration;

use defmt::*;
use embassy_executor::Spawner;
use embassy_stm32::bind_interrupts;
use embassy_stm32::ipcc::{Config, ReceiveInterruptHandler, TransmitInterruptHandler};
use embassy_stm32::rcc::WPAN_DEFAULT;
use embassy_stm32_wpan::hci::event::command::{CommandComplete, ReturnParameters};
use embassy_stm32_wpan::hci::host::uart::{Packet, UartHci};
use embassy_stm32_wpan::hci::host::{AdvertisingFilterPolicy, EncryptionKey, HostHci, OwnAddressType};
use embassy_stm32_wpan::hci::types::AdvertisingType;
use embassy_stm32_wpan::hci::vendor::command::gap::{
    AddressType, AuthenticationRequirements, DiscoverableParameters, GapCommands, IoCapability, LocalName, Pin, Role,
    SecureConnectionSupport,
};
use embassy_stm32_wpan::hci::vendor::command::gatt::{
    AddCharacteristicParameters, AddServiceParameters, CharacteristicEvent, CharacteristicPermission,
    CharacteristicProperty, EncryptionKeySize, GattCommands, ServiceType, UpdateCharacteristicValueParameters, Uuid,
    WriteResponseParameters,
};
use embassy_stm32_wpan::hci::vendor::command::hal::{ConfigData, HalCommands, PowerLevel};
use embassy_stm32_wpan::hci::vendor::event::command::VendorReturnParameters;
use embassy_stm32_wpan::hci::vendor::event::{self, AttributeHandle, VendorEvent};
use embassy_stm32_wpan::hci::{BdAddr, Event};
use embassy_stm32_wpan::lhci::LhciC1DeviceInformationCcrp;
use embassy_stm32_wpan::sub::ble::Ble;
use embassy_stm32_wpan::TlMbox;
use {defmt_rtt as _, panic_probe as _};

bind_interrupts!(struct Irqs{
    IPCC_C1_RX => ReceiveInterruptHandler;
    IPCC_C1_TX => TransmitInterruptHandler;
});

const BLE_GAP_DEVICE_NAME_LENGTH: u8 = 7;

extern crate alloc;
use talc::{ClaimOnOom, Span, Talc, Talck};
extern crate tinyrlibc;
use tinyrlibc as _;
static mut ARENA: [u8; 10000] = [0; 10000];
#[global_allocator]
static ALLOCATOR: Talck<spin::Mutex<()>, ClaimOnOom> = Talc::new(unsafe {
    // if we're in a hosted environment, the Rust runtime may allocate before
    // main() is called, so we need to initialize the arena automatically
    ClaimOnOom::new(Span::from_const_array(core::ptr::addr_of!(ARENA)))
})
.lock();
use embassy_stm32::time::Hertz;
use embassy_stm32::spi::Spi;
use embassy_stm32::dma::NoDma;
use embassy_stm32::gpio::Output;
use embassy_stm32::gpio::Level;
use embassy_stm32::gpio::Speed;
use embassy_time::Delay;
use embedded_hal_bus::spi::ExclusiveDevice;
use embassy_stm32::peripherals::SPI1;
use embassy_stm32::peripherals::PA4;
use core::cell::RefCell;
use crate::adapter::SpiAdapter;
use embassy_stm32::exti::ExtiInput;
use embassy_stm32::gpio::Input;
use embassy_stm32::gpio::Pull;
use a121_rs::radar::Radar;
use embassy_time::Timer;
type SpiDeviceMutex = ExclusiveDevice<Spi<'static, embassy_stm32::mode::Blocking>, Output<'static>, Delay>;
static mut SPI_DEVICE: Option<RefCell<SpiAdapter<SpiDeviceMutex>>> = None;

#[embassy_executor::main]
async fn main(_spawner: Spawner) {
    info!("Initializing peripherals");
    let mut config = embassy_stm32::Config::default();
    config.rcc = WPAN_DEFAULT;
    let p = embassy_stm32::init(config);

    info!("Initializing XE121");
    let exclusive_device = {
        let xe121_spi = {
            let mut spi_configuration = embassy_stm32::spi::Config::default();
            spi_configuration.frequency = Hertz(3_000_000);
            Spi::new_blocking(
                p.SPI1,
                p.PA5, // SCK
                p.PA7, // MOSI
                p.PA6, // MISO
                spi_configuration,
            )
        };

        let chip_select = Output::new(p.PA4, Level::High, Speed::VeryHigh);
        ExclusiveDevice::new(xe121_spi, chip_select, Delay)
    };

    unsafe { SPI_DEVICE = Some(RefCell::new(SpiAdapter::new(exclusive_device))) };
    let spi_mut_ref = unsafe { SPI_DEVICE.as_mut().unwrap() };

    info!("RSS Version: {}", a121_rs::radar::rss_version());

    let interrupt = ExtiInput::new(p.PC12, p.EXTI12, Pull::Up);
    let enable = Output::new(p.PA0, Level::Low, Speed::VeryHigh);
    let mut radar = Radar::new(1, spi_mut_ref.get_mut(), interrupt, enable, Delay).await;
    info!("Radar enabled");

    let mut buffer = [0u8; 2560];
    let mut calibration = loop {
        buffer.fill(0);
        if let Ok(calibration) = radar.calibrate().await {
            if let Ok(()) = calibration.validate_calibration() {
                info!("Calibration is valid");
                break calibration;
            } else {
                warn!("Calibration is invalid");
                warn!("Calibration result: {:?}", calibration);
            }
        } else {
            warn!("Calibration failed");
        }
        Timer::after(embassy_time::Duration::from_millis(1)).await;
    };
    info!("Calibration complete!");

    let mut radar = radar.prepare_sensor(&mut calibration).unwrap();

    let config = Config::default();
    let mut mbox = TlMbox::init(p.IPCC, Irqs, config);

    let sys_event = mbox.sys_subsystem.read().await;
    info!("sys event: {}", sys_event.payload());

    let _ = mbox.sys_subsystem.shci_c2_ble_init(Default::default()).await;

    info!("resetting BLE...");
    mbox.ble_subsystem.reset().await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("config public address...");
    mbox.ble_subsystem
        .write_config_data(&ConfigData::public_address(get_bd_addr()).build())
        .await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("config random address...");
    mbox.ble_subsystem
        .write_config_data(&ConfigData::random_address(get_random_addr()).build())
        .await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("config identity root...");
    mbox.ble_subsystem
        .write_config_data(&ConfigData::identity_root(&get_irk()).build())
        .await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("config encryption root...");
    mbox.ble_subsystem
        .write_config_data(&ConfigData::encryption_root(&get_erk()).build())
        .await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("config tx power level...");
    mbox.ble_subsystem.set_tx_power_level(PowerLevel::ZerodBm).await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("GATT init...");
    mbox.ble_subsystem.init_gatt().await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("GAP init...");
    mbox.ble_subsystem
        .init_gap(Role::PERIPHERAL, false, BLE_GAP_DEVICE_NAME_LENGTH)
        .await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("set IO capabilities...");
    mbox.ble_subsystem.set_io_capability(IoCapability::DisplayConfirm).await;
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("set authentication requirements...");
    mbox.ble_subsystem
        .set_authentication_requirement(&AuthenticationRequirements {
            bonding_required: false,
            keypress_notification_support: false,
            mitm_protection_required: false,
            encryption_key_size_range: (8, 16),
            fixed_pin: Pin::Requested,
            identity_address_type: AddressType::Public,
            secure_connection_support: SecureConnectionSupport::Optional,
        })
        .await
        .unwrap();
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("set scan response data...");
    mbox.ble_subsystem.le_set_scan_response_data(b"TXTX").await.unwrap();
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    info!("set scan response data...");
    mbox.ble_subsystem.le_set_scan_response_data(b"TXTX").await.unwrap();
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    defmt::info!("initializing services and characteristics...");
    let mut ble_context = init_gatt_services(&mut mbox.ble_subsystem).await.unwrap();
    defmt::info!("{}", ble_context);

    let discovery_params = DiscoverableParameters {
        advertising_type: AdvertisingType::ConnectableUndirected,
        advertising_interval: Some((Duration::from_millis(100), Duration::from_millis(100))),
        address_type: OwnAddressType::Public,
        filter_policy: AdvertisingFilterPolicy::AllowConnectionAndScan,
        local_name: Some(LocalName::Complete(b"TXTX")),
        advertising_data: &[],
        conn_interval: (None, None),
    };

    info!("set discoverable...");
    mbox.ble_subsystem.set_discoverable(&discovery_params).await.unwrap();
    let response = mbox.ble_subsystem.read().await;
    defmt::debug!("{}", response);

    loop {
        let response = mbox.ble_subsystem.read().await;
        defmt::debug!("{}", response);

        if let Ok(Packet::Event(event)) = response {
            match event {
                Event::LeConnectionComplete(_) => {
                    defmt::info!("connected");
                }
                Event::DisconnectionComplete(_) => {
                    defmt::info!("disconnected");
                    ble_context.is_subscribed = false;
                    mbox.ble_subsystem.set_discoverable(&discovery_params).await.unwrap();
                }
                Event::Vendor(vendor_event) => match vendor_event {
                    VendorEvent::AttReadPermitRequest(read_req) => {
                        defmt::info!("read request received {}, allowing", read_req);
                        let mut buffer = [0u8; 256 * 3];
                        if let Err(e) = radar.measure(&mut buffer).await {
                            info!("Error... {}", e);
                        } else {
                            info!("Data... {}", buffer);
                        }
                        mbox.ble_subsystem.update_characteristic_value(&UpdateCharacteristicValueParameters {
                            service_handle: ble_context.service_handle,
                            characteristic_handle: ble_context.chars.read,
                            offset: 0,
                            value: &buffer[0..4]
                        }).await.unwrap();
                        
                        let response = mbox.ble_subsystem.read().await;
                        defmt::warn!("{}", response);

                        mbox.ble_subsystem.allow_read(read_req.conn_handle).await
                    }
                    VendorEvent::AttWritePermitRequest(write_req) => {
                        defmt::info!("write request received {}, allowing", write_req);
                        mbox.ble_subsystem
                            .write_response(&WriteResponseParameters {
                                conn_handle: write_req.conn_handle,
                                attribute_handle: write_req.attribute_handle,
                                status: Ok(()),
                                value: write_req.value(),
                            })
                            .await
                            .unwrap()
                    }
                    VendorEvent::GattAttributeModified(attribute) => {
                        defmt::info!("{}", ble_context);
                        if attribute.attr_handle.0 == ble_context.chars.notify.0 + 2 {
                            if attribute.data()[0] == 0x01 {
                                defmt::info!("subscribed");
                                ble_context.is_subscribed = true;
                            } else {
                                defmt::info!("unsubscribed");
                                ble_context.is_subscribed = false;
                            }
                        }
                    }
                    _ => {}
                },
                _ => {}
            }
        }
    }
}

fn get_bd_addr() -> BdAddr {
    let mut bytes = [0u8; 6];

    let lhci_info = LhciC1DeviceInformationCcrp::new();
    bytes[0] = (lhci_info.uid64 & 0xff) as u8;
    bytes[1] = ((lhci_info.uid64 >> 8) & 0xff) as u8;
    bytes[2] = ((lhci_info.uid64 >> 16) & 0xff) as u8;
    bytes[3] = lhci_info.device_type_id;
    bytes[4] = (lhci_info.st_company_id & 0xff) as u8;
    bytes[5] = (lhci_info.st_company_id >> 8 & 0xff) as u8;

    BdAddr(bytes)
}

fn get_random_addr() -> BdAddr {
    let mut bytes = [0u8; 6];

    let lhci_info = LhciC1DeviceInformationCcrp::new();
    bytes[0] = (lhci_info.uid64 & 0xff) as u8;
    bytes[1] = ((lhci_info.uid64 >> 8) & 0xff) as u8;
    bytes[2] = ((lhci_info.uid64 >> 16) & 0xff) as u8;
    bytes[3] = 0;
    bytes[4] = 0x6E;
    bytes[5] = 0xED;

    BdAddr(bytes)
}

const BLE_CFG_IRK: [u8; 16] = [
    0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0, 0x12, 0x34, 0x56, 0x78, 0x9a, 0xbc, 0xde, 0xf0,
];
const BLE_CFG_ERK: [u8; 16] = [
    0xfe, 0xdc, 0xba, 0x09, 0x87, 0x65, 0x43, 0x21, 0xfe, 0xdc, 0xba, 0x09, 0x87, 0x65, 0x43, 0x21,
];

fn get_irk() -> EncryptionKey {
    EncryptionKey(BLE_CFG_IRK)
}

fn get_erk() -> EncryptionKey {
    EncryptionKey(BLE_CFG_ERK)
}

#[derive(defmt::Format)]
pub struct BleContext {
    pub service_handle: AttributeHandle,
    pub chars: CharHandles,
    pub is_subscribed: bool,
}

#[derive(defmt::Format)]
pub struct CharHandles {
    pub read: AttributeHandle,
    pub write: AttributeHandle,
    pub notify: AttributeHandle,
}

pub async fn init_gatt_services(ble_subsystem: &mut Ble) -> Result<BleContext, ()> {
    let service_handle = gatt_add_service(ble_subsystem, Uuid::Uuid16(0x500)).await?;

    let read = gatt_add_char(
        ble_subsystem,
        service_handle,
        Uuid::Uuid16(0x501),
        CharacteristicProperty::READ,
        Some(b"Hello aa bbsda from embassy!"),
    )
    .await?;

    let write = gatt_add_char(
        ble_subsystem,
        service_handle,
        Uuid::Uuid16(0x502),
        CharacteristicProperty::WRITE_WITHOUT_RESPONSE | CharacteristicProperty::WRITE | CharacteristicProperty::READ,
        None,
    )
    .await?;

    let notify = gatt_add_char(
        ble_subsystem,
        service_handle,
        Uuid::Uuid16(0x503),
        CharacteristicProperty::NOTIFY | CharacteristicProperty::READ,
        None,
    )
    .await?;

    Ok(BleContext {
        service_handle,
        is_subscribed: false,
        chars: CharHandles { read, write, notify },
    })
}

async fn gatt_add_service(ble_subsystem: &mut Ble, uuid: Uuid) -> Result<AttributeHandle, ()> {
    ble_subsystem
        .add_service(&AddServiceParameters {
            uuid,
            service_type: ServiceType::Primary,
            max_attribute_records: 8,
        })
        .await;
    let response = ble_subsystem.read().await;
    defmt::debug!("{}", response);

    if let Ok(Packet::Event(Event::CommandComplete(CommandComplete {
        return_params:
            ReturnParameters::Vendor(VendorReturnParameters::GattAddService(event::command::GattService {
                service_handle,
                ..
            })),
        ..
    }))) = response
    {
        Ok(service_handle)
    } else {
        Err(())
    }
}

async fn gatt_add_char(
    ble_subsystem: &mut Ble,
    service_handle: AttributeHandle,
    characteristic_uuid: Uuid,
    characteristic_properties: CharacteristicProperty,
    default_value: Option<&[u8]>,
) -> Result<AttributeHandle, ()> {
    ble_subsystem
        .add_characteristic(&AddCharacteristicParameters {
            service_handle,
            characteristic_uuid,
            characteristic_properties,
            characteristic_value_len: 32,
            security_permissions: CharacteristicPermission::empty(),
            gatt_event_mask: CharacteristicEvent::all(),
            encryption_key_size: EncryptionKeySize::with_value(7).unwrap(),
            is_variable: true,
        })
        .await;
    let response = ble_subsystem.read().await;
    defmt::debug!("{}", response);

    if let Ok(Packet::Event(Event::CommandComplete(CommandComplete {
        return_params:
            ReturnParameters::Vendor(VendorReturnParameters::GattAddCharacteristic(event::command::GattCharacteristic {
                characteristic_handle,
                ..
            })),
        ..
    }))) = response
    {
        if let Some(value) = default_value {
            ble_subsystem
                .update_characteristic_value(&UpdateCharacteristicValueParameters {
                    service_handle,
                    characteristic_handle,
                    offset: 0,
                    value,
                })
                .await
                .unwrap();

            let response = ble_subsystem.read().await;
            defmt::debug!("{}", response);
        }
        Ok(characteristic_handle)
    } else {
        Err(())
    }
}
