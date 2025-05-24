/*
 * Copyright (c) 2025 Kareem Fahmi
 * SPDX-License-Identifier: Apache-2.0
 */

 `default_nettype none

module spi_peripheral (
    input wire clk,     // clock
    input wire rst_n,    // active-low reset
    input wire nCS,      // active-low chip select
    input wire SCLK,     // SPI clock
    input wire COPI,     // controller out peripheral in

    // output registers to pwm module
    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

    // register map constants
    localparam en_reg_out_7_0_addr  = 7'h00;
    localparam en_reg_out_15_8_addr = 7'h01;
    localparam en_reg_pwm_7_0_addr  = 7'h02;
    localparam en_reg_pwm_15_8_addr = 7'h03;
    localparam pwm_duty_cycle_addr  = 7'h04;

    // CDC synchronization registers
    reg [1:0] nCS_sync;
    reg [1:0] SCLK_sync;
    reg [1:0] COPI_sync;

    // SPI transaction registers
    reg [4:0] SCLK_count;
    reg [15:0] data_stream;

    always @(posedge clk or negedge rst_n) begin
        // rst_n falling edge
        if (!rst_n) begin
            // reset all register values
            en_reg_out_7_0  <= '0;
            en_reg_out_15_8 <= '0;
            en_reg_pwm_7_0  <= '0;
            en_reg_pwm_15_8 <= '0;
            pwm_duty_cycle  <= '0;
            nCS_sync  <= '0;
            SCLK_sync <= '0;
            COPI_sync <= '0;
        end
        // clk rising edge
        else begin
            // shift SPI values into CDC sync registers
            nCS_sync  <= {nCS_sync[0], nCS};
            SCLK_sync <= {SCLK_sync[0], SCLK};
            COPI_sync <= {COPI_sync[0], COPI};

            // nCS falling edge - transaction begin
            if (nCS_sync == 2'b10) begin
                data_stream <= '0;
                SCLK_count <= '0;
            end

            // SCLK rising edge - read COPI
            else if (SCLK_sync == 2'b01) begin
                // only sample data 16 times for SPI packet
                if (SCLK_count < 5'd16) begin
                    data_stream <= {data_stream[14:0], COPI};
                    SCLK_count <= SCLK_count +1;
                end
            end

            // check for completed transaction
            /* requirements:
                1. 16 completed SCLK cycles (full transaction)
                2. nCS rising edge (transaction ended)
                3. R/W bit set to 1 (to denote write)
            */
            if (SCLK_count == 5'd16 && nCS_sync == 2'b01 && data_stream[15]) begin
                case (data_stream[14:8])
                        en_reg_out_7_0_addr:  en_reg_out_7_0  <= data_stream[7:0];
                        en_reg_out_15_8_addr: en_reg_out_15_8 <= data_stream[7:0];
                        en_reg_pwm_7_0_addr:  en_reg_pwm_7_0  <= data_stream[7:0];
                        en_reg_pwm_15_8_addr: en_reg_pwm_15_8 <= data_stream[7:0];
                        pwm_duty_cycle_addr:  pwm_duty_cycle  <= data_stream[7:0];
                        default: ; // ignore if improper address was provided
                endcase
            end
        end
    end
endmodule