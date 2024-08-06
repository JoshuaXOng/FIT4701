#![no_std]
#![no_main]

use core::cell::RefCell;

use a121_rs::detector::distance::RadarDistanceDetector;
use a121_rs::radar;
use a121_rs::radar::Radar;
use defmt::{info, warn};
use embassy_executor::Spawner;
use embassy_stm32::dma::NoDma;
use embassy_stm32::exti::ExtiInput;
use embassy_stm32::gpio::{Input, Level, Output, Pull, Speed};
use embassy_stm32::peripherals::{PB6, SPI1};
use embassy_stm32::rcc::{
    Clocks, LsConfig, Pll, PllMul, PllPDiv, PllPreDiv, PllQDiv, PllRDiv, PllSource,
};
use embassy_stm32::spi::{Config, Spi};
use embassy_stm32::time::Hertz;
use embassy_time::{Delay, Duration, Timer};
use embedded_hal_bus::spi::ExclusiveDevice;
use num::complex::Complex32;
use radar::rss_version;
use talc::{ClaimOnOom, Span, Talc, Talck};
use {defmt_rtt as _, panic_probe as _};

use crate::adapter::SpiAdapter;

extern crate alloc;
extern crate tinyrlibc;
use tinyrlibc as _;

mod adapter;
pub mod io;

static mut ARENA: [u8; 10000] = [0; 10000];

#[global_allocator]
static ALLOCATOR: Talck<spin::Mutex<()>, ClaimOnOom> = Talc::new(unsafe {
    // if we're in a hosted environment, the Rust runtime may allocate before
    // main() is called, so we need to initialize the arena automatically
    ClaimOnOom::new(Span::from_const_array(core::ptr::addr_of!(ARENA)))
})
.lock();

type SpiDeviceMutex = ExclusiveDevice<Spi<'static, SPI1, NoDma, NoDma>, Output<'static, PB6>, Delay>;
static mut SPI_DEVICE: Option<RefCell<SpiAdapter<SpiDeviceMutex>>> = None;

#[embassy_executor::main]
async fn main(spawner: Spawner) {
    info!("Initializing peripherals");
    let p = {
        let mut board_configuration = embassy_stm32::Config::default();
//        board_configuration.rcc.hsi = true;
//        board_configuration.rcc.hse = None;
//        board_configuration.rcc.sys = embassy_stm32::rcc::Sysclk::HSI;
//        board_configuration.rcc.pll_src = embassy_stm32::rcc::PllSource::HSI;
//        board_configuration.rcc.pll = None;
//        board_configuration.rcc.plli2s = None;
//        board_configuration.rcc.pllsai = None;
//        board_configuration.rcc.ahb_pre = embassy_stm32::rcc::AHBPrescaler::DIV1;
//        board_configuration.rcc.apb1_pre = embassy_stm32::rcc::APBPrescaler::DIV1;
//        board_configuration.rcc.apb2_pre = embassy_stm32::rcc::APBPrescaler::DIV1;
//        board_configuration.rcc.ls = embassy_stm32::rcc::LsConfig {
//            rtc: embassy_stm32::rcc::RtcClockSource::LSI,
//            lsi: true, lse: None
//        };
        embassy_stm32::init(board_configuration)
    };

    info!("Initializing XE121");
    let exclusive_device = {
        let xe121_spi = {
            let mut spi_configuration = Config::default();
            spi_configuration.frequency = Hertz(3_000_000);
            Spi::new(
                p.SPI1,
                p.PA5, // SCK
                p.PA7, // MOSI
                p.PA6, // MISO
                NoDma,
                NoDma,
                spi_configuration,
            )
        };

        let chip_select = Output::new(p.PB6, Level::High, Speed::VeryHigh);
        ExclusiveDevice::new(xe121_spi, chip_select, Delay)
    };

    unsafe { SPI_DEVICE = Some(RefCell::new(SpiAdapter::new(exclusive_device))) };
    let spi_mut_ref = unsafe { SPI_DEVICE.as_mut().unwrap() };

    info!("RSS Version: {}", rss_version());

    let interrupt = ExtiInput::new(Input::new(p.PA9, Pull::Up), p.EXTI9);
    let enable = Output::new(p.PB0, Level::Low, Speed::VeryHigh);
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
        Timer::after(Duration::from_millis(1)).await;
    };

    info!("Calibration complete!");

    let mut radar = radar.prepare_sensor(&mut calibration).unwrap();

    loop {
        let mut buffer = [0u8; 256 * 3];
        if let Err(e) = radar.measure(&mut buffer).await {
            info!("Error... {}", e);
        } else {
            info!("Data... {}", buffer);
        }
    }

//    let mut distance = RadarDistanceDetector::new(&mut radar);
//    let mut buffer = [0u8; 2560 * 3];
//    let mut static_call_result = [0u8; 2560];
//    let mut dynamic_call_result = distance
//        .calibrate_detector(&calibration, &mut buffer, &mut static_call_result)
//        .await
//        .unwrap();
//
//    let button = Input::new(p.PC13, Pull::Down);
//    let button = ExtiInput::new(button, p.EXTI13);
//    spawner.spawn(io::button_task(button)).unwrap();
//
//    loop {
//        info!("c");
//        // Timer::after(Duration::from_millis(200)).await;
//        'inner: loop {
//            info!("d");
//            distance.prepare_detector(&calibration, &mut buffer).unwrap();
//            //distance.measure().await.unwrap();
//            info!("e");
//
//            if let Ok(res) = distance.process_data(
//                &mut buffer,
//                &mut static_call_result,
//                &mut dynamic_call_result,
//            ) {
//                if res.num_distances() > 0 {
//                    info!(
//                        "{} Distances found:\n{:?}",
//                        res.num_distances(),
//                        res.distances()
//                    );
//                }
//                if res.calibration_needed() {
//                    info!("Calibration needed");
//                    break 'inner;
//                }
//            } else {
//                warn!("Failed to process data");
//            }
//        }
//        info!("f");
//        let calibration = distance.calibrate().await.unwrap();
//        info!("g");
//        dynamic_call_result = distance
//            .update_calibration(&calibration, &mut buffer)
//            .await
//            .unwrap();
//    }
}

#[no_mangle]
pub extern "C" fn __hardfp_cosf(f: f32) -> f32 {
    libm::cosf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_sinf(f: f32) -> f32 {
    libm::sinf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_roundf(f: f32) -> f32 {
    libm::roundf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_sqrtf(f: f32) -> f32 {
    libm::sqrtf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_powf(f: f32, g: f32) -> f32 {
    libm::powf(f, g)
}

#[no_mangle]
pub extern "C" fn __hardfp_cexpf(f: Complex32) -> Complex32 {
    f.exp()
}

#[no_mangle]
pub extern "C" fn __hardfp_cabsf(f: f32) -> f32 {
    libm::fabsf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_atanf(f: f32) -> f32 {
    libm::atanf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_floorf(f: f32) -> f32 {
    libm::floorf(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_log10f(f: f32) -> f32 {
    libm::log10f(f)
}

#[no_mangle]
pub extern "C" fn __hardfp_exp2f(f: f32) -> f32 {
    libm::exp2f(f)
}
