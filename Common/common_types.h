#pragma once

#include <stdint.h>

typedef enum
{
    STATUS_OK = 0,
    STATUS_ERROR = 1,
    STATUS_BUSY = 2,
    STATUS_TIMEOUT = 3,
    STATUS_UNSUPPORTED = 4
} Status_t;

