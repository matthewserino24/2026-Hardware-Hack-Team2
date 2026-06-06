#pragma once

#include <stdint.h>
#include "Common/common_types.h"

typedef struct
{
    float ax;
    float ay;
    float az;
    float gx;
    float gy;
    float gz;
} MPU6050_Raw_t;

typedef struct
{
    float pitch;
    float roll;
} MPU6050_Attitude_t;

/*
 * MPU6050 uses a 7-bit I2C address of 0x68 or 0x69 depending on AD0.
 * This driver assumes the default address 0x68 unless changed in source.
 */

Status_t MPU6050_Init(void);
Status_t MPU6050_ReadWhoAmI(uint8_t *id);
Status_t MPU6050_ReadRaw(MPU6050_Raw_t *raw);
Status_t MPU6050_ReadAttitude(MPU6050_Attitude_t *att);
