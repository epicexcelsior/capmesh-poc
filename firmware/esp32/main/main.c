#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "esp_mac.h"
#include "capabilities/led_capability.h"
#include "capabilities/contact_capability.h"
#include "protocol/capmesh_dispatcher.h"
#include "protocol/receipt_identity.h"
#include "transport/ble_transport.h"
#include "transport/http_transport.h"
#include "esp_netif.h"
#include "esp_event.h"

static const char *TAG = "CAPMESH_APP";

void app_main(void)
{
    ESP_LOGI(TAG, "==================================================");
    ESP_LOGI(TAG, "  CapMesh ESP32-C6 Provider Node Booting         ");
    ESP_LOGI(TAG, "==================================================");

    // 1. Initialize NVS
    // A storage failure must not silently erase a pinned device identity.
    esp_err_t ret = nvs_flash_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Storage initialization failed: %s. Storage is preserved.", esp_err_to_name(ret));
        return;
    }
    // Stop without a panic dump, which can disclose private material from crypto memory.
    if (receipt_identity_init() != ESP_OK) return;

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // 2. Derive unique device ID from Base MAC
    uint8_t mac[6];
    esp_read_mac(mac, ESP_MAC_BT);
    char device_id[32];
    snprintf(device_id, sizeof(device_id), "esp32-c6-%02x%02x", mac[4], mac[5]);
    ESP_LOGI(TAG, "Device ID: %s (Base MAC: %02x:%02x:%02x:%02x:%02x:%02x)",
             device_id, mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

    // 3. Initialize Capabilities (Actuators)
    ESP_ERROR_CHECK(led_capability_init());
    ESP_ERROR_CHECK(contact_capability_init());

    // 4. Initialize Protocol Dispatcher
    ESP_ERROR_CHECK(capmesh_dispatcher_init(device_id));
    capmesh_dispatcher_set_auth_required(true);

    // 5. Initialize BLE Transport
    ESP_ERROR_CHECK(capmesh_ble_transport_init(device_id));

    // 6. Initialize Wi-Fi SoftAP + HTTP Transport
    char ap_ssid[32];
    snprintf(ap_ssid, sizeof(ap_ssid), "CAPMESH_%02X%02X", mac[4], mac[5]);
    ESP_ERROR_CHECK(capmesh_http_transport_init(ap_ssid));

    ESP_LOGI(TAG, "CapMesh Dual Transport Node online! (BLE: %s, Wi-Fi: %s)", device_id, ap_ssid);
}
