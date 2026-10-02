#pragma once
#include <stdbool.h>
#include "esp_err.h"
#include "sdkconfig.h"

// Read only. GPIO9 is the legacy BOOT demonstration; external wiring requires board verification.
#define FIELDPROOF_CONTACT_GPIO CONFIG_FIELDPROOF_CONTACT_GPIO
#define FIELDPROOF_STRINGIFY_INNER(value) #value
#define FIELDPROOF_STRINGIFY(value) FIELDPROOF_STRINGIFY_INNER(value)
#define FIELDPROOF_CONTACT_SENSOR "gpio" FIELDPROOF_STRINGIFY(FIELDPROOF_CONTACT_GPIO) "-contact"
#if FIELDPROOF_CONTACT_GPIO == 9
#define FIELDPROOF_CONTACT_DESCRIPTION "Fresh GPIO9 contact at demo-gate (BOOT button stand-in)"
#else
#define FIELDPROOF_CONTACT_DESCRIPTION "Fresh " FIELDPROOF_CONTACT_SENSOR " input at demo-gate"
#endif
_Static_assert(FIELDPROOF_CONTACT_GPIO == 0 || FIELDPROOF_CONTACT_GPIO == 1 ||
               FIELDPROOF_CONTACT_GPIO == 2 || FIELDPROOF_CONTACT_GPIO == 3 ||
               FIELDPROOF_CONTACT_GPIO == 6 || FIELDPROOF_CONTACT_GPIO == 7 ||
               FIELDPROOF_CONTACT_GPIO == 9 ||
               (FIELDPROOF_CONTACT_GPIO >= 18 && FIELDPROOF_CONTACT_GPIO <= 23),
               "Select a supported read-only FieldProof contact GPIO");
#define FIELDPROOF_CONTACT_SAMPLES 5

esp_err_t contact_capability_init(void);
void contact_capability_sample(bool *closed, int *stable_samples);
