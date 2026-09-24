#include "capabilities/led_capability.h"
#include "driver/gpio.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

static const char *TAG = "CAP_LED";

esp_err_t led_capability_init(void)
{
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << CAPMESH_LED_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    esp_err_t err = gpio_config(&io_conf);
    if (err == ESP_OK) {
        gpio_set_level(CAPMESH_LED_GPIO, 0);
        ESP_LOGI(TAG, "LED capability initialized on GPIO %d", CAPMESH_LED_GPIO);
    }
    return err;
}

esp_err_t led_capability_blink(int duration_s, int count, int *blinks_completed)
{
    if (duration_s <= 0) {
        duration_s = 3;
    }
    if (count <= 0) {
        count = 5;
    }

    ESP_LOGI(TAG, "Executing led.blink: duration=%ds, count=%d", duration_s, count);

    int cycle_ms = (duration_s * 1000) / count;
    if (cycle_ms < 50) {
        cycle_ms = 50;
    }
    int on_ms = cycle_ms / 2;
    int off_ms = cycle_ms - on_ms;

    int done = 0;
    for (int i = 0; i < count; i++) {
        gpio_set_level(CAPMESH_LED_GPIO, 1);
        vTaskDelay(pdMS_TO_TICKS(on_ms));
        gpio_set_level(CAPMESH_LED_GPIO, 0);
        vTaskDelay(pdMS_TO_TICKS(off_ms));
        done++;
    }

    if (blinks_completed) {
        *blinks_completed = done;
    }

    ESP_LOGI(TAG, "led.blink finished: %d blinks performed", done);
    return ESP_OK;
}
