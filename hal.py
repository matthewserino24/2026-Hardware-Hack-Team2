"""
Thin physical-interface helpers built on machine.*.
"""

from machine import I2C, Pin, PWM
import utime

from config import I2C_BUS, I2C_FREQ, I2C_SCL_PIN, I2C_SDA_PIN


def make_i2c():
    return I2C(I2C_BUS, scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN), freq=I2C_FREQ)


def sleep_us(us):
    utime.sleep_us(us)


def sleep_ms(ms):
    utime.sleep_ms(ms)


def ticks_ms():
    return utime.ticks_ms()


def ticks_diff(a, b):
    return utime.ticks_diff(a, b)

