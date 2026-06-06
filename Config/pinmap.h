#pragma once

/*
 * Board pin mapping.
 * Replace these with the actual CubeMX-generated pin names once the hardware
 * wiring is finalized.
 */

// IMU (MPU6050)
#define IMU_I2C_SCL_PIN        "TODO"
#define IMU_I2C_SDA_PIN        "TODO"

// Temperature sensor (MCP9808)
#define TEMP_I2C_SCL_PIN       "TODO"
#define TEMP_I2C_SDA_PIN       "TODO"

// Ultrasonic sensor (HC-SR04)
#define HC_TRIG_PORT           "TODO"
#define HC_TRIG_PIN            "TODO"
#define HC_ECHO_PORT           "TODO"
#define HC_ECHO_PIN            "TODO"
#define HC_ECHO_TIMER_CHANNEL   (0u)

// Servo (SG90)
#define SERVO_PWM_PIN          "TODO"

// Speaker
#define SPEAKER_PWM_PIN        "TODO"
