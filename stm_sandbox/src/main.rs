#![no_std]
#![no_main]

use panic_halt as _;

use stm32f4xx_hal::{gpio::Speed, pac, prelude::*, spi::{Mode, Phase, Polarity, Spi}};
use cortex_m_rt::entry;
use rtt_target::{rtt_init_print, rprintln};

#[entry]
fn main() -> ! {
    rtt_init_print!();

    let board_peripherals = pac::Peripherals::take().unwrap();
    let gpioa = board_peripherals.GPIOA.split();
    let gpiob = board_peripherals.GPIOB.split();

    // let mut pa9 = gpioa.pa0.into_push_pull_output(); // PA9, a.k.a, D8. Interrupt line. 

    let mut pb0 = gpiob.pb0.into_push_pull_output(); // A3, a.k.a, PB0. Sensor enablement (active high). TODO: ADC?
    pb0.set_high(); 
    rprintln!("pb0 is {:?}", pb0.get_state());

    let mut pb6 = gpiob.pb6.into_push_pull_output(); // PB6, a.k.a, D10. Slave select.
    pb6.set_low();
    rprintln!("pb6 is {:?}", pb6.get_state());

    let mut xe121_spi = Spi::new(
        board_peripherals.SPI1, // XE121 connects to SPI1 of Nucleo board.
        (
            gpioa.pa5.into_alternate().speed(Speed::VeryHigh), // PA5, a.k.a, D13.
            gpioa.pa6.into_alternate().speed(Speed::VeryHigh) // PA6, a.k.a, D12.
                .internal_pull_up(true), // TODO: When do you want to enable this?
            gpioa.pa7.into_alternate().speed(Speed::VeryHigh) // PA7, a.k.a., D11.
                .internal_pull_up(true) // TODO: When do you want to enable this?
        ), 
        Mode {
            polarity: Polarity::IdleHigh, // TODO: IdleHigh is presumably active low, correct?
            phase: Phase::CaptureOnSecondTransition, // "MISO changes value on the falling edge".
                                                    
        }, 
        3.MHz(), // Max is 50 MHz
        &board_peripherals.RCC.constrain().cfgr.freeze()
    );
    xe121_spi.enable(true);

    let gpioc = board_peripherals.GPIOC.split();
    let mut led = gpioc.pc13.into_push_pull_output();

    loop {
        let mut a121_readings = [12; 4];
        rprintln!("Ahh... {:?}", a121_readings); 
        if let Err(e) = xe121_spi.read(&mut a121_readings) {
            rprintln!("Failed to get sensor readings... {:?}", e); 
        } else {
            rprintln!("Sensor readings... {:?}", a121_readings); 
        }

        for _ in 0..10_000 {
            led.set_high();
        }
        for _ in 0..10_000 {
            led.set_low();
        }
    }
}
