# Project Context

## Target Hardware

* **Primary MCU/Processor**: STM32G474RE (Arm Cortex-M4F @ 170 MHz)
* **Secondary Processors**: None
* **Dev Board / Custom PCB**: STM32 Nucleo-G474RE
* **Board Revision**: Nucleo-G474RE

## Clock Configuration

* **HSE/HSI**: TBD
* **PLL Config**: TBD
* **System Clock Frequency**: TBD

## Pin Mapping / GPIO Assignments

* MPU-6050

  * SDA → I2C SDA (TBD)
  * SCL → I2C SCL (TBD)
* SG90 Servo

  * PWM Signal → Timer Output Pin (TBD)

## Memory Layout

* **Flash Size**: 512 KB
* **RAM Size**: 128 KB
* **Linker Script Regions**: Default STM32G474RE memory layout

## Peripherals & Interfaces

* GPIO
* I2C
* Timer/PWM
* UART (Debug Console)

## External Devices & Sensors

* MPU-6050 6-axis IMU
* SG90 Micro Servo Motor

## Communication Protocols

* **Protocol**: I2C (MPU-6050)
* **Baud Rate / Mode**: Standard/Fast Mode (TBD)

## Software Stack

* **Build System**: STM32CubeIDE / CMake (TBD)
* **Compile Command**: TBD
* **HAL / Framework**: STM32Cube HAL
* **RTOS**: None (Bare Metal)
* **Toolchain**: ARM GCC (arm-none-eabi-gcc)
* **Compiler Flags**: TBD
* **External Libraries**:

  * MPU-6050 Driver
  * CMSIS

## Development Environment

* **Host OS**: Windows
* **IDE**: STM32CubeIDE
* **Debug Interface (SWD/JTAG)**: SWD
* **Debug Probe (ST-Link/J-Link/OpenOCD)**: On-board ST-Link

## Debug Configuration

* **GDB Server Command**: STM32CubeIDE Default
* **GDB Executable**: arm-none-eabi-gdb
* **Firmware ELF Path**: TBD
* **GDB Server Port**: Default STM32CubeIDE Configuration

## Power Management

* **Sleep Modes**: TBD
* **Power Domains**: Default STM32G4 Configuration
* **Battery / Power Source**:

  * USB 5V
  * External 5V Supply (optional)

## Boot Configuration

* **Bootloader**: STM32 System Bootloader
* **OTA Mechanism**: None

## Interrupt Configuration

* **NVIC Priority Groups**: TBD
* **Key ISRs**:

  * I2C Events
  * Timer Update Events
  * SysTick

## Compliance & Standards

* None currently

## SDK / Library Paths

* STM32CubeG4 SDK
* CMSIS

## Supporting Devices

* USB Cable
* Breadboard
* Jumper Wires

## Project Notes

Goal:
Build a closed-loop attitude stabilization system using MPU-6050 and SG90 servo.

System Flow:
MPU-6050 → STM32G474RE → Sensor Fusion → PID Controller → SG90 Servo

Features:

* Read accelerometer and gyroscope data
* Estimate pitch and roll angles
* Implement complementary or Kalman filter
* Drive SG90 using PWM
* Demonstrate active stabilization and attitude compensation


## Project Notes
