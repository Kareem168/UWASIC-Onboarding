# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import Logic
from cocotb.types import LogicArray

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    dut._log.info("Start PWM frequency test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # set registers
    await send_spi_transaction(dut, 1, 0x00, 0x01) # output enable
    await send_spi_transaction(dut, 1, 0x02, 0x01) # pwm enable
    await send_spi_transaction(dut, 1, 0x04, 0x80) # set duty cycle to 50%
    await ClockCycles(dut.clk, 5)


    # make sure start time is sampled at rising edge
    start = cocotb.utils.get_sim_time(units="ns")
    timeout = 1e6
    # wait for next falling edge
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            return -1

    # wait for next rising edge
    while dut.uo_out.value == 0:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            return -1

    # start sample time
    sample_start = cocotb.utils.get_sim_time(units="ns")

    # wait for next falling edge
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)

    # wait for next rising edge
    while dut.uo_out.value == 0:
        await ClockCycles(dut.clk, 1)

    # calculate period in seconds
    period = (cocotb.utils.get_sim_time(units="ns") - sample_start) * 1e-9
    frequency = 1/period

    dut._log.info(f'Frequency: {frequency}')

    assert frequency >= 2970 and frequency <= 3030, "frequency is out of bounds"  

    dut._log.info("PWM Frequency test completed successfully")


@cocotb.test()
async def test_pwm_duty(dut):
    dut._log.info("Start PWM duty cycle test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # set registers
    await send_spi_transaction(dut, 1, 0x00, 0x01) # output enable
    await send_spi_transaction(dut, 1, 0x02, 0x01) # pwm enable
    await send_spi_transaction(dut, 1, 0x04, 0x80) # set duty cycle to 50%
    await ClockCycles(dut.clk, 5)

    # CAUCLUATING PERIOD

    # make sure start time is sampled at rising edge
    start = cocotb.utils.get_sim_time(units="ns")
    timeout = 1e6
    # wait for next falling edge
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            return -1

    # wait for next rising edge
    while dut.uo_out.value == 0:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            return -1

    # start sample time
    sample_start = cocotb.utils.get_sim_time(units="ns")

    # wait for next falling edge
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)

    # wait for next rising edge
    while dut.uo_out.value == 0:
        await ClockCycles(dut.clk, 1)

    # calculate period
    period = cocotb.utils.get_sim_time(units="ns") - sample_start

    # CALCULATE DUTY CYCLE FOR 50%

    # make sure start time is sampled at rising edge
    start = cocotb.utils.get_sim_time(units="ns")
    timeout = 1e6
    # wait for next falling edge
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            return -1

    # wait for next rising edge
    while dut.uo_out.value == 0:
        await ClockCycles(dut.clk, 1)
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            return -1

    # start sample time
    sample_start = cocotb.utils.get_sim_time(units="ns")

    # wait for next falling edge
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)

    # calculate the high time
    high_time = cocotb.utils.get_sim_time(units="ns") - sample_start

    # calculate duty cycle
    duty_cycle = (high_time/period) * 100

    dut._log.info(f'Duty cycle value (should be 50%): {duty_cycle}%')
    assert duty_cycle == 50, "duty cycle should be 50%"

    # CHECK DUTY CYCLE FOR 0%
    await send_spi_transaction(dut, 1, 0x04, 0x00) # set duty cycle to 0%
    start = cocotb.utils.get_sim_time(units="ns")
    timeout = 1e4

    # check that there are no rising edges
    while dut.uo_out.value == 0:
        await ClockCycles(dut.clk, 1)
        if (dut.uo_out.value != 0):
            assert dut.uo_out.value == 0, "signal should not go high for 0 duty cycle"
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            break

    dut._log.info("Duty Cycle 0% Verified")

    # CHECK DUTY CYCLE FOR 0%
    await send_spi_transaction(dut, 1, 0x04, 0xFF) # set duty cycle to 0%
    start = cocotb.utils.get_sim_time(units="ns")
    timeout = 1e4

    # check that there are no rising edges
    while dut.uo_out.value != 0:
        await ClockCycles(dut.clk, 1)
        if (dut.uo_out.value == 0):
            assert dut.uo_out.value != 0, "signal should not go low for 100 duty cycle"
        if (cocotb.utils.get_sim_time(units="ns") - start > timeout):
            break

    dut._log.info("Duty Cycle 100% Verified")

    dut._log.info("PWM Duty Cycle test completed successfully")
