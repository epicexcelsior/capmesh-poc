#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"

static const char *TAG = "CAPMESH_BOOT";

#define LED_GPIO 8

void app_main(void)
{
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  CapMesh Phase 0: Hardware Truth Test  ");
    ESP_LOGI(TAG, "  Target: ESP32-C6 (GPIO %d LED)       ", LED_GPIO);
    ESP_LOGI(TAG, "========================================");

    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << LED_GPIO),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));

    ESP_LOGI(TAG, "Starting initial 5-blink verification...");
    for (int i = 1; i <= 5; i++) {
        gpio_set_level(LED_GPIO, 1);
        ESP_LOGI(TAG, "LED ON (blink %d/5)", i);
        vTaskDelay(pdMS_TO_TICKS(300));
        gpio_set_level(LED_GPIO, 0);
        ESP_LOGI(TAG, "LED OFF (blink %d/5)", i);
        vTaskDelay(pdMS_TO_TICKS(300));
    }

    ESP_LOGI(TAG, "Phase 0 local blink test complete! Entering standby heartbeat...");
    while (1) {
        gpio_set_level(LED_GPIO, 1);
        vTaskDelay(pdMS_TO_TICKS(100));
        gpio_set_level(LED_GPIO, 0);
        vTaskDelay(pdMS_TO_TICKS(1900));
    }
}
