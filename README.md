# ZH_Base_Framework

This repository currently contains two parallel implementations of the same hardware abstraction idea:

1. A `MicroPython` track built around `config.py`, `hal.py`, `mpu6050.py`, `mcp9808.py`, `ultrasonic.py`, `servo_feedback.py`, and `ht16k33.py`
2. A `C / HAL` track built around `BSP/`, `Drivers/`, `Services/`, `Algo/`, and `App/`

Both tracks follow the same layered structure:

- `BSP / hal`: board-level physical interfaces
- `Drivers`: single-device drivers
- `Services`: multi-device data aggregation
- `Algo`: control and estimation logic
- `App / main`: final application flow

## Purpose

The goal of this framework is to prepare reusable low-level infrastructure before the final project direction is fixed. It already covers the main hardware on the STM32G474RE platform:

- `MPU6050`
- `MCP9808`
- `HC-SR04`
- `SG90`
- `Speaker`
- `HT16K33`

That means future application ideas such as obstacle avoidance, orientation display, feedback control, or temperature display can all build on the same base.

## MicroPython Track

### `config.py`

Purpose:
- Central place for pins, I2C addresses, timing constants, servo angles, and thresholds

Implemented:
- `I2C_BUS`, `I2C_ID`, `I2C_FREQ`, `I2C_SCL_PIN`, `I2C_SDA_PIN`
- `MPU6050_ADDR`, `MCP9808_ADDR`, `HT16K33_ADDR`
- `HCSR04_TRIG_PIN`, `HCSR04_ECHO_PIN`
- `SG90_PWM_PIN`, `SERVO_PIN`
- `LOOP_PERIOD_MS`, `HEADING_TOLERANCE_DEG`
- `WARNING_DISTANCE_CM`, `DANGER_DISTANCE_CM`

Example:
```python
import config
print(config.I2C_FREQ)
```

### `hal.py`

Purpose:
- Thin board-level helper layer for MicroPython

Implemented:
- `make_i2c()`
- `sleep_us(us)`
- `sleep_ms(ms)`
- `ticks_ms()`
- `ticks_diff(a, b)`

Example:
```python
from hal import make_i2c, ticks_ms

i2c = make_i2c()
now = ticks_ms()
```

### `mpu6050.py`

Purpose:
- Low-level MPU6050 MicroPython driver

Implemented:
- `MPU6050.__init__(i2c, addr=0x68)`
- `who_am_i()`
- `accel()`
- `gyro()`
- `temperature()`
- `read_gyro_z_dps()`
- `read_all()`
- `read_raw()`

Example:
```python
from hal import make_i2c
from mpu6050 import MPU6050

i2c = make_i2c()
imu = MPU6050(i2c)
print(imu.who_am_i())
print(imu.read_raw())
```

### `imu.py`

Purpose:
- Higher-level heading integration wrapper built on top of `mpu6050.py`

Implemented:
- `IMU.__init__(i2c)`
- `calibrate()`
- `zero_heading()`
- `update(dt_s)`
- `heading`

Example:
```python
from hal import make_i2c
from imu import IMU
import utime

imu = IMU(make_i2c())
imu.calibrate()

last = utime.ticks_ms()
while True:
    now = utime.ticks_ms()
    dt = utime.ticks_diff(now, last) / 1000.0
    last = now
    imu.update(dt)
    print(imu.heading)
```

### `mcp9808.py`

Purpose:
- MCP9808 temperature sensor driver

Implemented:
- `MCP9808.__init__(i2c, addr=0x18)`
- `manufacturer_id()`
- `device_id()`
- `temperature()`
- `configure(value=0x0000)`
- `set_resolution(value=0x03)`

Example:
```python
from hal import make_i2c
from mcp9808 import MCP9808

sensor = MCP9808(make_i2c())
print(sensor.temperature())
```

### `ultrasonic.py`

Purpose:
- HC-SR04 ultrasonic distance driver

Implemented:
- `HCSR04.__init__(trig_pin, echo_pin)`
- `distance_cm()`
- `distance_cm_raw()`
- `read_raw_cm()`
- `read_cm()`
- `Ultrasonic` compatibility alias

Example:
```python
from ultrasonic import HCSR04

sonar = HCSR04("D7", "D8")
print(sonar.distance_cm())
```

### `servo_feedback.py`

Purpose:
- SG90 haptic feedback / steering driver

Implemented:
- `ServoFeedback.__init__(pin)`
- `set_angle(angle_deg)`
- `neutral()`
- `stop()`
- `steer(heading_error_deg)`
- `tap_left()`
- `tap_right()`
- `warning_pulse()`
- `warning_pattern(distance_cm)`
- `danger_pattern()`
- `tick()`

Example:
```python
from servo_feedback import ServoFeedback

servo = ServoFeedback("D6")
servo.neutral()
servo.tap_left()
servo.tick()
```

### `ht16k33.py`

Purpose:
- HT16K33 display driver

Implemented:
- `HT16K33.__init__(i2c, addr=0x70, brightness=15)`
- `clear()`
- `show()`
- `set_brightness(level)`
- `set_pixel(x, y, on=True)`
- `set_digit(pos, segments, dot=False)`
- `set_colon(on=True)`
- `print_str(text, colon=False)`
- `print_int(value, pad=True)`
- `print_float(value, decimal_places=1)`
- `display_number(number)`

Example:
```python
from hal import make_i2c
from ht16k33 import HT16K33

display = HT16K33(make_i2c())
display.print_float(23.5, decimal_places=1)
display.show()
```

### `main.py`, `obstacle.py`, `route.py`

Purpose:
- Application-level integration logic

Implemented:
- `main.py`: startup sequence and main loop
- `obstacle.py`: obstacle state classification
- `route.py`: waypoint routing and navigation control flow

Example:
```python
import main

main.run()
```

## C / HAL Track

### `BSP/bsp_board.h` / `BSP/bsp_board.c`

Purpose:
- Board init and generic delay / tick interface

Interface:
- `BSP_Board_Init()`
- `BSP_GetTickMs()`
- `BSP_DelayMs(ms)`

Example:
```c
BSP_Board_Init();
BSP_DelayMs(20);
```

### `BSP/bsp_uart_log.h` / `BSP/bsp_uart_log.c`

Purpose:
- UART logging helpers

Interface:
- `BSP_Log_Init()`
- `BSP_Log_Print(level, fmt, ...)`
- `LOG_INFO(...)`
- `LOG_WARN(...)`
- `LOG_ERROR(...)`

Example:
```c
LOG_INFO("Temp=%.2f", temp);
```

### `BSP/bsp_i2c.h` / `BSP/bsp_i2c.c`

Purpose:
- Board-level I2C abstraction

Interface:
- `BSP_I2C_Init()`
- `BSP_I2C_Write(dev_addr, reg_addr, data, len)`
- `BSP_I2C_Read(dev_addr, reg_addr, data, len)`
- `BSP_I2C_WriteRaw(dev_addr, data, len)`

Example:
```c
uint8_t id = 0;
BSP_I2C_Read(0x68, 0x75, &id, 1);
```

### `BSP/bsp_gpio.h` / `BSP/bsp_gpio.c`

Purpose:
- Board-level GPIO abstraction

Interface:
- `BSP_GPIO_Init()`
- `BSP_GPIO_Write(port, pin, level)`
- `BSP_GPIO_Read(port, pin, level)`

Example:
```c
BSP_GPIO_Write(port, pin, GPIO_LEVEL_HIGH);
```

### `BSP/bsp_timer.h` / `BSP/bsp_timer.c`

Purpose:
- Microsecond timing helpers

Interface:
- `BSP_Timer_Init()`
- `BSP_Timer_GetMicros()`
- `BSP_Timer_DelayUs(us)`

Example:
```c
uint32_t t0 = BSP_Timer_GetMicros();
```

### `BSP/bsp_pwm.h` / `BSP/bsp_pwm.c`

Purpose:
- Shared PWM abstraction for servo and speaker

Interface:
- `BSP_PWM_Init()`
- `BSP_PWM_SetFrequency(channel, freq_hz)`
- `BSP_PWM_SetDutyCycle(channel, duty_cycle)`
- `BSP_PWM_Start(channel)`
- `BSP_PWM_Stop(channel)`
- `BSP_PWM_SetChannelConfig(config)`
- `BSP_PWM_GetChannelConfig(channel)`

Example:
```c
BSP_PWM_SetFrequency(0, 50);
BSP_PWM_SetDutyCycle(0, 0.5f);
BSP_PWM_Start(0);
```

### `Drivers/IMU/mpu6050.h` / `Drivers/IMU/mpu6050.c`

Purpose:
- MPU6050 C driver

Interface:
- `MPU6050_Init()`
- `MPU6050_ReadWhoAmI(id)`
- `MPU6050_ReadRaw(raw)`
- `MPU6050_ReadAttitude(att)`

Example:
```c
uint8_t id;
MPU6050_Init();
MPU6050_ReadWhoAmI(&id);
```

### `Drivers/Temperature/mcp9808.h` / `Drivers/Temperature/mcp9808.c`

Purpose:
- MCP9808 temperature driver

Interface:
- `MCP9808_Init()`
- `MCP9808_ReadTemperature(celsius)`

Example:
```c
float temp;
MCP9808_Init();
MCP9808_ReadTemperature(&temp);
```

### `Drivers/Distance/hcsr04.h` / `Drivers/Distance/hcsr04.c`

Purpose:
- HC-SR04 distance driver

Interface:
- `HCSR04_Init()`
- `HCSR04_ReadDistanceCm(distance_cm)`
- `HCSR04_Trigger()`
- `HCSR04_CaptureEdge(edge)`
- `HCSR04_SetConfig(config)`
- `HCSR04_GetConfig()`

Example:
```c
float dist;
HCSR04_Init();
HCSR04_ReadDistanceCm(&dist);
```

### `Drivers/Actuator/sg90.h` / `Drivers/Actuator/sg90.c`

Purpose:
- SG90 servo driver

Interface:
- `SG90_Init()`
- `SG90_SetAngle(angle_deg)`
- `SG90_SetPulseUs(pulse_us)`

Example:
```c
SG90_Init();
SG90_SetAngle(90.0f);
```

### `Drivers/Audio/speaker.h` / `Drivers/Audio/speaker.c`

Purpose:
- Speaker / buzzer driver

Interface:
- `Speaker_Init()`
- `Speaker_Beep(freq_hz, duration_ms)`
- `Speaker_SetTone(freq_hz)`
- `Speaker_Stop()`
- `Speaker_SetVolume(duty_percent)`
- `Speaker_SetConfig(config)`
- `Speaker_GetConfig()`

Example:
```c
Speaker_Init();
Speaker_Beep(1000, 200);
```

### `Drivers/Display/ht16k33.h` / `Drivers/Display/ht16k33.c`

Purpose:
- HT16K33 display driver

Interface:
- `HT16K33_Init()`
- `HT16K33_Clear()`
- `HT16K33_SetPixel(x, y, on)`
- `HT16K33_SetBrightness(brightness)`
- `HT16K33_DisplayNumber(number)`
- `HT16K33_SetConfig(config)`
- `HT16K33_GetConfig()`

Example:
```c
HT16K33_Init();
HT16K33_DisplayNumber(42);
```

### `Algo/pid.h` / `Algo/pid.c`

Purpose:
- Generic PID controller

Interface:
- `PID_Init(pid, kp, ki, kd, out_min, out_max)`
- `PID_Update(pid, target, current)`
- `PID_Reset(pid)`

Example:
```c
PID_t pid;
PID_Init(&pid, 1.0f, 0.0f, 0.0f, -100.0f, 100.0f);
float out = PID_Update(&pid, 10.0f, 7.5f);
```

### `Algo/filter.h` / `Algo/filter.c`

Purpose:
- Generic filter helpers

Interface:
- `Filter_Clamp(value, min_value, max_value)`
- `Filter_AlphaBlend(prev, current, alpha)`

Example:
```c
float v = Filter_Clamp(x, 0.0f, 1.0f);
```

### `Algo/attitude.h` / `Algo/attitude.c`

Purpose:
- Attitude storage and update layer

Interface:
- `Attitude_Init()`
- `Attitude_Update(ax, ay, az, gx, gy, gz, dt)`
- `Attitude_Get()`
- `Attitude_GetPitch()`
- `Attitude_GetRoll()`

Example:
```c
Attitude_Update(ax, ay, az, gx, gy, gz, dt);
float pitch = Attitude_GetPitch();
```

### `Services/sensor_service.h` / `Services/sensor_service.c`

Purpose:
- Aggregate multiple sensor readings

Interface:
- `SensorService_Init()`
- `SensorService_GetData()`

Example:
```c
SensorData_t data = SensorService_GetData();
```

### `Services/attitude_service.h` / `Services/attitude_service.c`

Purpose:
- Attitude service layer

Interface:
- `AttitudeService_Init()`
- `AttitudeService_GetData()`

Example:
```c
AttitudeService_Init();
```

### `Services/control_service.h` / `Services/control_service.c`

Purpose:
- PID-based control service

Interface:
- `ControlService_Init()`
- `ControlService_UpdateAngle(target_angle, current_angle)`

Example:
```c
float cmd = ControlService_UpdateAngle(90.0f, 87.0f);
```

### `Services/system_service.h` / `Services/system_service.c`

Purpose:
- System state management

Interface:
- `SystemService_Init()`
- `SystemService_GetState()`
- `SystemService_SetState(state)`

Example:
```c
SystemService_SetState(STATE_ACTIVE);
```

### `App/app.h` / `App/app.c`

Purpose:
- Application entry layer

Interface:
- `App_Init()`
- `App_Loop()`

Example:
```c
App_Init();
while (1) {
    App_Loop();
}
```

### `App/app_state.h` / `App/app_state.c`

Purpose:
- Application state storage

Interface:
- `AppState_Init()`
- `AppState_Get()`
- `AppState_Set(state)`

Example:
```c
AppState_Set(STATE_IDLE);
```

### `App/app_task.h` / `App/app_task.c`

Purpose:
- Single-step task wrapper

Interface:
- `AppTask_RunOnce()`

Example:
```c
AppTask_RunOnce();
```

## Recommended Startup Order

### MicroPython Track
1. `hal.make_i2c()`
2. `MPU6050`
3. `MCP9808`
4. `Ultrasonic` or `HCSR04`
5. `ServoFeedback`
6. `HT16K33`
7. `main.py`

### C Track
1. `BSP_Board_Init()`
2. `BSP_I2C_Init()`
3. `MPU6050_Init()`
4. `MCP9808_Init()`
5. `HCSR04_Init()`
6. `SG90_Init()`
7. `Speaker_Init()`
8. `HT16K33_Init()`
9. `SensorService_Init()`
10. `App_Init()`

## Notes

- This repository intentionally keeps both the Python-style and C-style framework.
- If the final project uses MicroPython, start with `config.py + hal.py + *.py`.
- If the final project uses STM32 HAL in C, start with `BSP + Drivers + Services + Algo + App`.
- The hardware definitions are aligned across both tracks, so the two implementations can be used as references for each other.
