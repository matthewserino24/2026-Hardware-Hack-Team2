#include "Drivers/Display/ht16k33.h"

#include "BSP/bsp_i2c.h"

#define HT16K33_DEFAULT_I2C_ADDR_7BIT   (0x70u)
#define HT16K33_CMD_SYSTEM_SETUP        (0x20u)
#define HT16K33_CMD_DISPLAY_SETUP       (0x80u)
#define HT16K33_CMD_DIMMING             (0xE0u)
#define HT16K33_CMD_BLINK               (0x80u)
#define HT16K33_CMD_OSC_ON              (0x01u)
#define HT16K33_CMD_DISPLAY_ON          (0x01u)

typedef struct
{
    char ch;
    uint8_t rows[5];
} HT16K33_Glyph_t;

static HT16K33_Config_t s_config = {
    .i2c_addr_7bit = HT16K33_DEFAULT_I2C_ADDR_7BIT,
    .brightness = 15u,
    .display_on = 1u
};

/*
 * HT16K33 internal RAM: 16 bytes.
 * For a typical 8x8 matrix, even addresses hold row bits and odd addresses are unused.
 * This buffer is kept here so the driver shape is ready for a real frame-buffered implementation.
 */
static uint8_t s_display_ram[16] = {0};

static const HT16K33_Glyph_t s_glyphs[] = {
    {'0', {0x7u, 0x5u, 0x5u, 0x5u, 0x7u}},
    {'1', {0x2u, 0x6u, 0x2u, 0x2u, 0x7u}},
    {'2', {0x7u, 0x1u, 0x7u, 0x4u, 0x7u}},
    {'3', {0x7u, 0x1u, 0x7u, 0x1u, 0x7u}},
    {'4', {0x5u, 0x5u, 0x7u, 0x1u, 0x1u}},
    {'5', {0x7u, 0x4u, 0x7u, 0x1u, 0x7u}},
    {'6', {0x7u, 0x4u, 0x7u, 0x5u, 0x7u}},
    {'7', {0x7u, 0x1u, 0x2u, 0x2u, 0x2u}},
    {'8', {0x7u, 0x5u, 0x7u, 0x5u, 0x7u}},
    {'9', {0x7u, 0x5u, 0x7u, 0x1u, 0x7u}},
    {'-', {0x0u, 0x0u, 0x7u, 0x0u, 0x0u}},
    {' ', {0x0u, 0x0u, 0x0u, 0x0u, 0x0u}},
};

static Status_t ht16k33_write_command(uint8_t command)
{
    return BSP_I2C_WriteRaw(s_config.i2c_addr_7bit, &command, 1u);
}

static Status_t ht16k33_write_ram(void)
{
    return BSP_I2C_WriteRaw(s_config.i2c_addr_7bit, s_display_ram, 16u);
}

static void ht16k33_clear_buffer(void)
{
    for (uint8_t i = 0; i < 16u; ++i)
    {
        s_display_ram[i] = 0u;
    }
}

static const HT16K33_Glyph_t *ht16k33_find_glyph(char ch)
{
    for (uint32_t i = 0; i < (uint32_t)(sizeof(s_glyphs) / sizeof(s_glyphs[0])); ++i)
    {
        if (s_glyphs[i].ch == ch)
        {
            return &s_glyphs[i];
        }
    }

    return &s_glyphs[sizeof(s_glyphs) / sizeof(s_glyphs[0]) - 1u];
}

static void ht16k33_draw_glyph(uint8_t x_offset, uint8_t y_offset, const HT16K33_Glyph_t *glyph)
{
    if (glyph == 0)
    {
        return;
    }

    for (uint8_t row = 0u; row < 5u; ++row)
    {
        for (uint8_t col = 0u; col < 3u; ++col)
        {
            if ((glyph->rows[row] & (1u << (2u - col))) != 0u)
            {
                uint8_t x = (uint8_t)(x_offset + col);
                uint8_t y = (uint8_t)(y_offset + row);
                if (x < 8u && y < 8u)
                {
                    uint8_t index = (uint8_t)(y * 2u);
                    s_display_ram[index] |= (uint8_t)(1u << x);
                }
            }
        }
    }
}

Status_t HT16K33_Init(void)
{
    if (BSP_I2C_Init() != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    /*
     * Power-up sequence:
     * 1. Oscillator on
     * 2. Display on
     * 3. Set brightness
     */
    if (ht16k33_write_command((uint8_t)(HT16K33_CMD_SYSTEM_SETUP | HT16K33_CMD_OSC_ON)) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (ht16k33_write_command((uint8_t)(HT16K33_CMD_DISPLAY_SETUP | HT16K33_CMD_DISPLAY_ON)) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    if (HT16K33_SetBrightness(s_config.brightness) != STATUS_OK)
    {
        return STATUS_ERROR;
    }

    ht16k33_clear_buffer();
    return ht16k33_write_ram();
}

Status_t HT16K33_Clear(void)
{
    ht16k33_clear_buffer();
    return ht16k33_write_ram();
}

Status_t HT16K33_SetPixel(uint8_t x, uint8_t y, uint8_t on)
{
    if (x >= 8u || y >= 8u)
    {
        return STATUS_ERROR;
    }

    /*
     * Frame buffer mapping:
     * byte index = row * 2, bit = column
     * This matches a simple 8x8 matrix layout and can be adapted later if the
     * wiring matrix is rotated or mirrored.
     */
    uint8_t index = (uint8_t)(y * 2u);
    uint8_t mask = (uint8_t)(1u << x);

    if (on != 0u)
    {
        s_display_ram[index] |= mask;
    }
    else
    {
        s_display_ram[index] &= (uint8_t)~mask;
    }

    return ht16k33_write_ram();
}

Status_t HT16K33_SetBrightness(uint8_t brightness)
{
    if (brightness > 15u)
    {
        return STATUS_ERROR;
    }

    s_config.brightness = brightness;
    return ht16k33_write_command((uint8_t)(HT16K33_CMD_DIMMING | brightness));
}

Status_t HT16K33_DisplayNumber(int16_t number)
{
    char digits[4];
    uint8_t count = 0u;
    int16_t value = number;

    ht16k33_clear_buffer();

    if (value < 0)
    {
        value = (int16_t)(-value);
        digits[count++] = '-';
    }

    if (value >= 100)
    {
        /*
         * Keep the API predictable on an 8x8 display:
         * clamp large values to the last two digits so something useful is shown.
         */
        value = (int16_t)(value % 100);
    }

    if (value >= 10)
    {
        digits[count++] = (char)('0' + (value / 10));
        digits[count++] = (char)('0' + (value % 10));
    }
    else
    {
        digits[count++] = (char)('0' + value);
    }

    if (count == 1u)
    {
        ht16k33_draw_glyph(2u, 1u, ht16k33_find_glyph(digits[0]));
    }
    else if (count == 2u)
    {
        ht16k33_draw_glyph(0u, 1u, ht16k33_find_glyph(digits[0]));
        ht16k33_draw_glyph(4u, 1u, ht16k33_find_glyph(digits[1]));
    }
    else if (count == 3u)
    {
        /*
         * Negative two-digit number: keep the sign and both digits visible.
         */
        ht16k33_draw_glyph(0u, 1u, ht16k33_find_glyph(digits[0]));
        ht16k33_draw_glyph(3u, 1u, ht16k33_find_glyph(digits[1]));
        ht16k33_draw_glyph(5u, 1u, ht16k33_find_glyph(digits[2]));
    }

    return ht16k33_write_ram();
}

Status_t HT16K33_SetConfig(const HT16K33_Config_t *config)
{
    if (config == 0)
    {
        return STATUS_ERROR;
    }

    s_config = *config;
    return STATUS_OK;
}

const HT16K33_Config_t *HT16K33_GetConfig(void)
{
    return &s_config;
}
