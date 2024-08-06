#![no_std]
#![no_main]

use panic_halt as _;

use stm32f4xx_hal::{gpio::Speed, pac, prelude::*, spi::{Mode, Phase, Polarity, Spi}, timer::Timer};
use cortex_m_rt::entry;
use rtt_target::{rtt_init_print, rprintln};

#[entry]
fn main() -> ! {
    rtt_init_print!();

    let board_peripherals = pac::Peripherals::take().unwrap();
    let chip_peripherals = cortex_m::peripheral::Peripherals::take().unwrap();

    let clock_control = board_peripherals.RCC.constrain();
    let system_clocks = clock_control
        .cfgr
        .sysclk(180.MHz())
        .hclk(180.MHz())
        .pclk1(30.MHz())
        .pclk2(30.MHz())
        .freeze();

    let mut delay = Timer::syst(chip_peripherals.SYST, &system_clocks).delay();

    let gpioa = board_peripherals.GPIOA.split();
    let gpiob = board_peripherals.GPIOB.split();

    let mut pa9 = gpioa.pa0.into_push_pull_output(); // PA9, a.k.a, D8. Interrupt line. 

    let mut pb0 = gpiob.pb0.into_push_pull_output(); // A3, a.k.a, PB0. Sensor enablement (active high). TODO: ADC?
    pb0.set_high(); 
    rprintln!("pb0 is {:?}", pb0.get_state());

    let mut xe121_spi = Spi::new(
        board_peripherals.SPI1, // XE121 connects to SPI1 of Nucleo board.
        (
            gpioa.pa5.into_alternate().speed(Speed::VeryHigh), // PA5, a.k.a, D13.
            gpioa.pa6.into_alternate() // PA6, a.k.a, D12.
                .internal_pull_up(true), // TODO: When do you want to enable this?
            gpioa.pa7.into_alternate() // PA7, a.k.a., D11.
                .internal_pull_up(true) // TODO: When do you want to enable this?
        ), 
        Mode { // CPOL/CPHA = 0
            polarity: Polarity::IdleLow, 
            phase: Phase::CaptureOnFirstTransition, 
        }, 
        3.MHz(), // Max is 50 MHz
        &system_clocks
    );
    xe121_spi.enable(true);

    let mut a = embedded_hal_bus::spi::ExclusiveDevice::new(xe121_spi, gpioa.pa5.into_push_pull_output(), delay);
    let mut a = a.unwrap();
    let mut a = ExclusiveDevice_(a);
    a121_rs::radar::Radar::new(0, &mut a, &mut pa9, pb0, &mut delay);

    let mut slave_select = gpiob.pb6.into_push_pull_output(); // PB6, a.k.a, D10. Slave select.

    loop {
        slave_select.set_low();
        delay.delay_ns(2);

        let mut a121_readings = [0xaa; 16];
        if let Err(e) = xe121_spi.transfer(&mut a121_readings, &[0xd0; 16]) {
            rprintln!("Failed to get sensor readings... {:?}", e); 
        } else {
            rprintln!("Sensor readings... {:?}", a121_readings); 
        }

        slave_select.set_high();
    }
}

use embedded_hal::spi::Operation;
use embedded_hal::spi::SpiBus;
use embedded_hal::spi::SpiDevice;
use embedded_hal::spi::Error;
use embedded_hal::spi::ErrorType;
use embedded_hal::delay::DelayNs;
use embedded_hal::digital::OutputPin;

struct ExclusiveDevice_<BUS, CS, D>(embedded_hal_bus::spi::ExclusiveDevice<BUS, CS, D>);

impl<BUS, CS, D> ErrorType for ExclusiveDevice_<BUS, CS, D>
where BUS: ErrorType, CS: OutputPin, {
    type Error = embedded_hal::spi::ErrorKind;
}

impl<Word: Copy + 'static, BUS, CS, D> SpiDevice<Word> for ExclusiveDevice_<BUS, CS, D>
where BUS: SpiBus<Word>, CS: OutputPin, D: DelayNs {
    #[inline]
    fn transaction(&mut self, operations: &mut [Operation<'_, Word>]) -> Result<(), Self::Error> {
        self.transaction(operations).map_err(|e| e.kind())
    }
}
