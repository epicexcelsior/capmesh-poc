#pragma once
#include <stdbool.h>
#include "esp_err.h"

// GPIO9 is the ESP32-C6 boot strap. Read it only. Do not drive it.
#define FIELDPROOF_CONTACT_GPIO 9
#define FIELDPROOF_CONTACT_SAMPLES 5

esp_err_t contact_capability_init(void);
void contact_capability_sample(bool *closed, int *stable_samples);
