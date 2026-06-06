#include "Drivers/IMU/mpu6050.h"
#include "BSP/bsp_i2c.h"
#include <math.h>

#define MPU6050_I2C_ADDR_7BIT      (0x68u)
#define MPU6050_REG_SMPLRT_DIV      (0x19u)
#define MPU6050_REG_CONFIG          (0x1Au)
#define MPU6050_REG_GYRO_CONFIG     (0x1Bu)
#define MPU6050_REG_ACCEL_CONFIG    (0x1Cu)
#define MPU6050_REG_ACCEL_XOUT_H    (0x3Bu)
#define MPU6050_REG_PWR_MGMT_1      (0x6Bu)
#define MPU6050_REG_WHO_AM_I        (0x75u)
#define MPU6050_WHO_AM_I_VALUE      (0x68u)

#define MPU6050_ACCEL_LSB_PER_G     (16384.0f)
#define MPU6050_GYRO_LSB_PER_DPS    (131.0f)
#define MPU6050_ALPHA               (0.98f)

static float s_pitch = 0.0f;
static float s_roll = 0.0f;

static Status_t mpu6050_write_reg(uint8_t reg, uint8_t value)
{
    return BSP_I2C_Write(MPU6050_I2C_ADDR_7BIT, reg, &value, 1u);
}

static Status_t mpu6050_read_reg(uint8_t reg, uint8_t *value)
{
    return BSP_I2C_Read(MPU6050_I2C_ADDR_7BIT, reg, value, 1u);
}

static Status_t mpu6050_read_bytes(uint8_t reg, uint8_t *data, uint16_t len)
{
    return BSP_I2C_Read(MPU6050_I2C_ADDR_7BIT, reg, data, len);
}

Status_t MPU6050_Init(void)
{
    uint8_t who_am_i = 0;

    if (BSP_I2C_Init() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (MPU6050_ReadWhoAmI(&who_am_i) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (who_am_i != MPU6050_WHO_AM_I_VALUE)
    {
        return STATUS_ERROR;
    }

    if (mpu6050_write_reg(MPU6050_REG_PWR_MGMT_1, 0x00u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (mpu6050_write_reg(MPU6050_REG_SMPLRT_DIV, 0x07u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (mpu6050_write_reg(MPU6050_REG_CONFIG, 0x06u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (mpu6050_write_reg(MPU6050_REG_GYRO_CONFIG, 0x00u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (mpu6050_write_reg(MPU6050_REG_ACCEL_CONFIG, 0x00u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    s_pitch = 0.0f;
    s_roll = 0.0f;
    return STATUS_OK;
}

Status_t MPU6050_ReadWhoAmI(uint8_t *id)
{
    if (id == 0)
    {
        return STATUS_ERROR;
    }

    return mpu6050_read_reg(MPU6050_REG_WHO_AM_I, id);
}

Status_t MPU6050_ReadRaw(MPU6050_Raw_t *raw)
{
    if (raw == 0)
    {
        return STATUS_ERROR;
    }

    uint8_t buf[14] = {0};
    if (mpu6050_read_bytes(MPU6050_REG_ACCEL_XOUT_H, buf, 14u) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    int16_t ax_raw = (int16_t)((uint16_t)buf[0] << 8 | buf[1]);
    int16_t ay_raw = (int16_t)((uint16_t)buf[2] << 8 | buf[3]);
    int16_t az_raw = (int16_t)((uint16_t)buf[4] << 8 | buf[5]);
    int16_t gx_raw = (int16_t)((uint16_t)buf[8] << 8 | buf[9]);
    int16_t gy_raw = (int16_t)((uint16_t)buf[10] << 8 | buf[11]);
    int16_t gz_raw = (int16_t)((uint16_t)buf[12] << 8 | buf[13]);

    raw->ax = (float)ax_raw / MPU6050_ACCEL_LSB_PER_G;
    raw->ay = (float)ay_raw / MPU6050_ACCEL_LSB_PER_G;
    raw->az = (float)az_raw / MPU6050_ACCEL_LSB_PER_G;
    raw->gx = (float)gx_raw / MPU6050_GYRO_LSB_PER_DPS;
    raw->gy = (float)gy_raw / MPU6050_GYRO_LSB_PER_DPS;
    raw->gz = (float)gz_raw / MPU6050_GYRO_LSB_PER_DPS;

    return STATUS_OK;
}

Status_t MPU6050_ReadAttitude(MPU6050_Attitude_t *att)
{
    if (att == 0)
    {
        return STATUS_ERROR;
    }

    MPU6050_Raw_t raw;
    if (MPU6050_ReadRaw(&raw) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    /*
     * Complementary filter:
     * - accelerometer provides long-term reference
     * - gyro provides short-term stability
     * dt is intentionally omitted in this first skeleton and can be folded in
     * once the scheduler/timer source is defined.
     */
    float accel_pitch = 0.0f;
    float accel_roll = 0.0f;

    if ((raw.ay != 0.0f) || (raw.az != 0.0f))
    {
        accel_pitch = atan2f(-raw.ax, sqrtf((raw.ay * raw.ay) + (raw.az * raw.az)));
        accel_roll = atan2f(raw.ay, raw.az);
    }

    s_pitch = MPU6050_ALPHA * s_pitch + (1.0f - MPU6050_ALPHA) * accel_pitch;
    s_roll = MPU6050_ALPHA * s_roll + (1.0f - MPU6050_ALPHA) * accel_roll;

    att->pitch = s_pitch;
    att->roll = s_roll;
    return STATUS_OK;
}
