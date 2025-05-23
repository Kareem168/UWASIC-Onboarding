/*
 * Copyright (c) 2025 Kareem Fahmi
 * SPDX-License-Identifier: Apache-2.0
 */

 `default_nettype none

module spi_peripheral (
    input wire COPI,    // controller in, peripheral out
    input wire nCS,     // chip select
    input SCLK,         // clock
);

    reg [15:0] en_out
    reg [15:0] pwm_mode
    reg [7:0] pwm_duty_cycle

endmodule
