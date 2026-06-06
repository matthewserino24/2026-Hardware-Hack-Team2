# ZH_Base_Framework

副标题：`ZH_基础物理接口框架`

这份仓库当前分成两条线：

1. `MicroPython` 版本：`config.py` / `hal.py` / `mpu6050.py` / `mcp9808.py` / `ultrasonic.py` / `servo_feedback.py` / `ht16k33.py`
2. `C / HAL` 版本：`BSP/`、`Drivers/`、`Services/`、`Algo/`、`App/`

两条线表达的是同一套硬件分层思想：

- `BSP / hal` 负责板级物理接口
- `Drivers` 负责单个器件
- `Services` 负责多个器件的数据整合
- `Algo` 负责控制和解算
- `App / main` 负责最终业务流程

## 使用目标

这个框架的目标不是先定最终项目，而是先把这些硬件都接成稳定接口：

- `MPU6050`
- `MCP9808`
- `HC-SR04`
- `SG90`
- `Speaker`
- `HT16K33`

后续无论做云台、避障、姿态、温度显示、提示音，都可以在这套底座上继续加。

## MicroPython 版本

### `config.py`

用途：
- 统一存放板级引脚、I2C 地址、采样周期、舵机角度和阈值

实现了什么：
- `I2C_BUS`, `I2C_FREQ`, `I2C_SCL_PIN`, `I2C_SDA_PIN`
- `MPU6050_ADDR`, `MCP9808_ADDR`, `HT16K33_ADDR`
- `HCSR04_TRIG_PIN`, `HCSR04_ECHO_PIN`
- `SG90_PWM_PIN`
- `LOOP_PERIOD_MS`, `HEADING_TOLERANCE_DEG`
- `WARNING_DISTANCE_CM`, `DANGER_DISTANCE_CM`

怎么调用：
```python
import config
print(config.I2C_FREQ)
```

---

### `hal.py`

用途：
- 给上层模块提供薄封装的板级接口

实现了什么：
- `make_i2c()`
- `sleep_us(us)`
- `sleep_ms(ms)`
- `ticks_ms()`
- `ticks_diff(a, b)`

怎么调用：
```python
from hal import make_i2c, ticks_ms
i2c = make_i2c()
now = ticks_ms()
```

---

### `mpu6050.py`

用途：
- MPU6050 的 MicroPython 驱动

实现了什么：
- `MPU6050.__init__(i2c, addr=0x68)`
- `who_am_i()`
- `calibrate()`
- `zero_heading()`
- `update(now_ms)`
- `heading()`
- `read_gyro_z_dps()`
- `read_raw()`

怎么调用：
```python
from hal import make_i2c
from mpu6050 import MPU6050

i2c = make_i2c()
imu = MPU6050(i2c)
imu.calibrate()
imu.update(time.ticks_ms())
print(imu.heading())
```

---

### `mcp9808.py`

用途：
- MCP9808 温度传感器驱动

实现了什么：
- `MCP9808.__init__(i2c, addr=0x18)`
- `manufacturer_id()`
- `device_id()`
- `temperature()`
- `configure(value=0x0000)`

怎么调用：
```python
from hal import make_i2c
from mcp9808 import MCP9808

temp = MCP9808(make_i2c())
print(temp.temperature())
```

---

### `ultrasonic.py`

用途：
- HC-SR04 超声波测距驱动

实现了什么：
- `Ultrasonic.__init__(trig_pin, echo_pin)`
- `read_raw_cm()`
- `read_cm()`

怎么调用：
```python
from ultrasonic import Ultrasonic
sensor = Ultrasonic("D7", "D8")
print(sensor.read_cm())
```

---

### `servo_feedback.py`

用途：
- SG90 舵机提示反馈层

实现了什么：
- `ServoFeedback.__init__(pwm_pin)`
- `neutral()`
- `stop()`
- `tap_left()`
- `tap_right()`
- `warning_pattern(distance_cm)`
- `danger_pattern()`
- `tick()`

怎么调用：
```python
from servo_feedback import ServoFeedback

servo = ServoFeedback("D6")
servo.neutral()
servo.tap_left()
servo.tick()
```

---

### `ht16k33.py`

用途：
- HT16K33 点阵显示驱动

实现了什么：
- `HT16K33.__init__(i2c, addr=0x70, brightness=8)`
- `clear()`
- `set_brightness(brightness)`
- `set_pixel(x, y, on=True)`
- `display_number(number)`

怎么调用：
```python
from hal import make_i2c
from ht16k33 import HT16K33

disp = HT16K33(make_i2c())
disp.display_number(23)
```

---

### `main.py`、`imu.py`、`obstacle.py`、`route.py`

用途：
- 这是远端 Python 分支里的主业务逻辑参考

现状：
- `main.py` 负责把 IMU、超声、舵机、路线状态串起来
- `imu.py` 负责 MPU6050 的姿态积分
- `obstacle.py` 负责距离阈值分类
- `route.py` 负责航点和转向状态机

怎么调用：
- `main.py` 作为入口运行
- 其他模块由 `main.py` 直接 import 后调用

注：
- 当前仓库里我补的是底层接口文件，`main.py` 这条线可以后续再按同样风格补回仓库

## C / HAL 版本

### `BSP/bsp_board.h` / `BSP/bsp_board.c`

用途：
- 板级初始化和通用延时 / tick

接口：
- `BSP_Board_Init()`
- `BSP_GetTickMs()`
- `BSP_DelayMs(ms)`

怎么调用：
```c
BSP_Board_Init();
BSP_DelayMs(20);
```

---

### `BSP/bsp_uart_log.h` / `BSP/bsp_uart_log.c`

用途：
- UART 调试日志

接口：
- `BSP_Log_Init()`
- `BSP_Log_Print(level, fmt, ...)`
- `LOG_INFO(...)`
- `LOG_WARN(...)`
- `LOG_ERROR(...)`

怎么调用：
```c
LOG_INFO("Temp=%.2f", temp);
```

---

### `BSP/bsp_i2c.h` / `BSP/bsp_i2c.c`

用途：
- 板级 I2C 抽象层

接口：
- `BSP_I2C_Init()`
- `BSP_I2C_Write(dev_addr, reg_addr, data, len)`
- `BSP_I2C_Read(dev_addr, reg_addr, data, len)`
- `BSP_I2C_WriteRaw(dev_addr, data, len)`

怎么调用：
```c
uint8_t id = 0;
BSP_I2C_Read(0x68, 0x75, &id, 1);
```

---

### `BSP/bsp_gpio.h` / `BSP/bsp_gpio.c`

用途：
- 板级 GPIO 抽象

接口：
- `BSP_GPIO_Init()`
- `BSP_GPIO_Write(port, pin, level)`
- `BSP_GPIO_Read(port, pin, level)`

怎么调用：
```c
BSP_GPIO_Write(port, pin, GPIO_LEVEL_HIGH);
```

---

### `BSP/bsp_timer.h` / `BSP/bsp_timer.c`

用途：
- 微秒级计时和延时抽象

接口：
- `BSP_Timer_Init()`
- `BSP_Timer_GetMicros()`
- `BSP_Timer_DelayUs(us)`

怎么调用：
```c
uint32_t t0 = BSP_Timer_GetMicros();
```

---

### `BSP/bsp_pwm.h` / `BSP/bsp_pwm.c`

用途：
- PWM 抽象层，给舵机和扬声器共用

接口：
- `BSP_PWM_Init()`
- `BSP_PWM_SetFrequency(channel, freq_hz)`
- `BSP_PWM_SetDutyCycle(channel, duty_cycle)`
- `BSP_PWM_Start(channel)`
- `BSP_PWM_Stop(channel)`
- `BSP_PWM_SetChannelConfig(config)`
- `BSP_PWM_GetChannelConfig(channel)`

怎么调用：
```c
BSP_PWM_SetFrequency(0, 50);
BSP_PWM_SetDutyCycle(0, 0.5f);
BSP_PWM_Start(0);
```

---

### `Drivers/IMU/mpu6050.h` / `Drivers/IMU/mpu6050.c`

用途：
- MPU6050 驱动

接口：
- `MPU6050_Init()`
- `MPU6050_ReadWhoAmI(id)`
- `MPU6050_ReadRaw(raw)`
- `MPU6050_ReadAttitude(att)`

怎么调用：
```c
uint8_t id;
MPU6050_Init();
MPU6050_ReadWhoAmI(&id);
```

---

### `Drivers/Temperature/mcp9808.h` / `Drivers/Temperature/mcp9808.c`

用途：
- MCP9808 温度驱动

接口：
- `MCP9808_Init()`
- `MCP9808_ReadTemperature(celsius)`

怎么调用：
```c
float temp;
MCP9808_Init();
MCP9808_ReadTemperature(&temp);
```

---

### `Drivers/Distance/hcsr04.h` / `Drivers/Distance/hcsr04.c`

用途：
- HC-SR04 测距驱动

接口：
- `HCSR04_Init()`
- `HCSR04_ReadDistanceCm(distance_cm)`
- `HCSR04_Trigger()`
- `HCSR04_CaptureEdge(edge)`
- `HCSR04_SetConfig(config)`
- `HCSR04_GetConfig()`

怎么调用：
```c
float dist;
HCSR04_Init();
HCSR04_ReadDistanceCm(&dist);
```

---

### `Drivers/Actuator/sg90.h` / `Drivers/Actuator/sg90.c`

用途：
- SG90 舵机驱动

接口：
- `SG90_Init()`
- `SG90_SetAngle(angle_deg)`
- `SG90_SetPulseUs(pulse_us)`

怎么调用：
```c
SG90_Init();
SG90_SetAngle(90.0f);
```

---

### `Drivers/Audio/speaker.h` / `Drivers/Audio/speaker.c`

用途：
- Speaker / buzzer 驱动

接口：
- `Speaker_Init()`
- `Speaker_Beep(freq_hz, duration_ms)`
- `Speaker_SetTone(freq_hz)`
- `Speaker_Stop()`
- `Speaker_SetVolume(duty_percent)`
- `Speaker_SetConfig(config)`
- `Speaker_GetConfig()`

怎么调用：
```c
Speaker_Init();
Speaker_Beep(1000, 200);
```

---

### `Drivers/Display/ht16k33.h` / `Drivers/Display/ht16k33.c`

用途：
- HT16K33 点阵 / 显示驱动

接口：
- `HT16K33_Init()`
- `HT16K33_Clear()`
- `HT16K33_SetPixel(x, y, on)`
- `HT16K33_SetBrightness(brightness)`
- `HT16K33_DisplayNumber(number)`
- `HT16K33_SetConfig(config)`
- `HT16K33_GetConfig()`

怎么调用：
```c
HT16K33_Init();
HT16K33_DisplayNumber(42);
```

---

### `Algo/pid.h` / `Algo/pid.c`

用途：
- 通用 PID 控制器

接口：
- `PID_Init(pid, kp, ki, kd, out_min, out_max)`
- `PID_Update(pid, target, current)`
- `PID_Reset(pid)`

怎么调用：
```c
PID_t pid;
PID_Init(&pid, 1.0f, 0.0f, 0.0f, -100.0f, 100.0f);
float out = PID_Update(&pid, 10.0f, 7.5f);
```

---

### `Algo/filter.h` / `Algo/filter.c`

用途：
- 通用滤波工具

接口：
- `Filter_Clamp(value, min_value, max_value)`
- `Filter_AlphaBlend(prev, current, alpha)`

怎么调用：
```c
float v = Filter_Clamp(x, 0.0f, 1.0f);
```

---

### `Algo/attitude.h` / `Algo/attitude.c`

用途：
- 姿态解算缓存

接口：
- `Attitude_Init()`
- `Attitude_Update(ax, ay, az, gx, gy, gz, dt)`
- `Attitude_Get()`
- `Attitude_GetPitch()`
- `Attitude_GetRoll()`

怎么调用：
```c
Attitude_Update(ax, ay, az, gx, gy, gz, dt);
float pitch = Attitude_GetPitch();
```

---

### `Services/sensor_service.h` / `Services/sensor_service.c`

用途：
- 汇总多个传感器数据

接口：
- `SensorService_Init()`
- `SensorService_GetData()`

怎么调用：
```c
SensorData_t data = SensorService_GetData();
```

---

### `Services/attitude_service.h` / `Services/attitude_service.c`

用途：
- 姿态服务层

接口：
- `AttitudeService_Init()`
- `AttitudeService_GetData()`

怎么调用：
```c
AttitudeService_Init();
```

---

### `Services/control_service.h` / `Services/control_service.c`

用途：
- 控制服务层，封装 PID

接口：
- `ControlService_Init()`
- `ControlService_UpdateAngle(target_angle, current_angle)`

怎么调用：
```c
float cmd = ControlService_UpdateAngle(90.0f, 87.0f);
```

---

### `Services/system_service.h` / `Services/system_service.c`

用途：
- 系统状态机

接口：
- `SystemService_Init()`
- `SystemService_GetState()`
- `SystemService_SetState(state)`

怎么调用：
```c
SystemService_SetState(STATE_ACTIVE);
```

---

### `App/app.h` / `App/app.c`

用途：
- 应用层入口

接口：
- `App_Init()`
- `App_Loop()`

怎么调用：
```c
App_Init();
while (1) {
    App_Loop();
}
```

---

### `App/app_state.h` / `App/app_state.c`

用途：
- 应用状态缓存

接口：
- `AppState_Init()`
- `AppState_Get()`
- `AppState_Set(state)`

怎么调用：
```c
AppState_Set(STATE_IDLE);
```

---

### `App/app_task.h` / `App/app_task.c`

用途：
- 单步任务执行封装

接口：
- `AppTask_RunOnce()`

怎么调用：
```c
AppTask_RunOnce();
```

## 推荐启动顺序

### MicroPython 线
1. `hal.make_i2c()`
2. `MPU6050`
3. `MCP9808`
4. `Ultrasonic`
5. `ServoFeedback`
6. `HT16K33`
7. `main.py`

### C 线
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

## 备注

- 现在仓库里同时保留了 Python 风格和 C 风格骨架。
- 如果最终项目确定走 MicroPython，优先用 `config.py + hal.py + *.py`。
- 如果最终项目确定走 STM32 HAL C，优先用 `BSP + Drivers + Services + Algo + App`。
- 两条线的硬件定义是一致的，可以互相对照，但不要直接混着改同一个入口层。

