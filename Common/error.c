#include "Common/error.h"

const char *Error_ToString(Status_t status)
{
    switch (status)
    {
        case STATUS_OK: return "OK";
        case STATUS_ERROR: return "ERROR";
        case STATUS_BUSY: return "BUSY";
        case STATUS_TIMEOUT: return "TIMEOUT";
        case STATUS_UNSUPPORTED: return "UNSUPPORTED";
        default: return "UNKNOWN";
    }
}

