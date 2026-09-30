#include "capabilities/contact_capability.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

esp_err_t contact_capability_init(void)
{
    gpio_config_t config = {
        .pin_bit_mask = 1ULL << FIELDPROOF_CONTACT_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    return gpio_config(&config);
}

void contact_capability_sample(bool *closed, int *stable_samples)
{
    // The BOOT button is a contact-demo stand-in, not a deployed gate sensor.
    *closed = gpio_get_level(FIELDPROOF_CONTACT_GPIO) == 0;
    *stable_samples = 1;
    for (int i = 1; i < FIELDPROOF_CONTACT_SAMPLES; i++) {
        vTaskDelay(pdMS_TO_TICKS(10));
        if ((gpio_get_level(FIELDPROOF_CONTACT_GPIO) == 0) == *closed) {
            (*stable_samples)++;
        }
    }
}
