#include "BSP/bsp_uart_log.h"
#include <stdio.h>

void BSP_Log_Init(void)
{
    // Hook UART here later.
}

void BSP_Log_Print(LogLevel_t level, const char *fmt, ...)
{
    const char *prefix = "[INFO]";
    if (level == LOG_LEVEL_WARN)
    {
        prefix = "[WARN]";
    }
    else if (level == LOG_LEVEL_ERROR)
    {
        prefix = "[ERROR]";
    }

    printf("%s ", prefix);

    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);

    printf("\r\n");
}

