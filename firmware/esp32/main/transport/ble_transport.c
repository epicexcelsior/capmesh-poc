#include "transport/ble_transport.h"
#include "protocol/capmesh_dispatcher.h"
#include "esp_log.h"
#include "host/ble_hs.h"
#include "host/ble_uuid.h"
#include "host/util/util.h"
#include "services/gap/ble_svc_gap.h"
#include "services/gatt/ble_svc_gatt.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_port_freertos.h"
#include <string.h>

static const char *TAG = "BLE_TRANS";

#define MAX_PAYLOAD_LEN 1024

// CapMesh UUIDs (16-bit)
static const ble_uuid16_t s_svc_uuid      = BLE_UUID16_INIT(0xCB00);
static const ble_uuid16_t s_manifest_uuid = BLE_UUID16_INIT(0xCB01);
static const ble_uuid16_t s_invoke_uuid   = BLE_UUID16_INIT(0xCB02);
static const ble_uuid16_t s_receipt_uuid  = BLE_UUID16_INIT(0xCB03);

static uint16_t s_manifest_val_handle;
static uint16_t s_invoke_val_handle;
static uint16_t s_receipt_val_handle;

static char s_manifest_buf[MAX_PAYLOAD_LEN] = {0};
static char s_receipt_buf[MAX_PAYLOAD_LEN] = "{\"protocol\":\"capmesh/0.1\",\"status\":\"idle\"}";
static char s_device_name[32] = "capmesh-c6";
static uint8_t s_own_addr_type;

static int gatt_svr_access(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg);

static const struct ble_gatt_svc_def s_gatt_svcs[] = {
    {
        .type = BLE_GATT_SVC_TYPE_PRIMARY,
        .uuid = &s_svc_uuid.u,
        .characteristics = (struct ble_gatt_chr_def[])
        {
            {
                // Manifest Characteristic (Read, Notify)
                .uuid = &s_manifest_uuid.u,
                .access_cb = gatt_svr_access,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_manifest_val_handle,
            },
            {
                // Invoke Characteristic (Write, Write No Rsp)
                .uuid = &s_invoke_uuid.u,
                .access_cb = gatt_svr_access,
                .flags = BLE_GATT_CHR_F_WRITE | BLE_GATT_CHR_F_WRITE_NO_RSP,
                .val_handle = &s_invoke_val_handle,
            },
            {
                // Receipt Characteristic (Read, Notify)
                .uuid = &s_receipt_uuid.u,
                .access_cb = gatt_svr_access,
                .flags = BLE_GATT_CHR_F_READ | BLE_GATT_CHR_F_NOTIFY,
                .val_handle = &s_receipt_val_handle,
            },
            {
                0, // End of characteristics
            }
        },
    },
    {
        0, // End of services
    },
};

static int gatt_svr_access(uint16_t conn_handle, uint16_t attr_handle,
                           struct ble_gatt_access_ctxt *ctxt, void *arg)
{
    int rc;

    if (attr_handle == s_manifest_val_handle) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            // Refresh manifest if empty
            if (strlen(s_manifest_buf) == 0) {
                capmesh_dispatcher_get_manifest(s_manifest_buf, sizeof(s_manifest_buf));
            }
            rc = os_mbuf_append(ctxt->om, s_manifest_buf, strlen(s_manifest_buf));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
        return BLE_ATT_ERR_UNLIKELY;
    }

    if (attr_handle == s_receipt_val_handle) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_READ_CHR) {
            rc = os_mbuf_append(ctxt->om, s_receipt_buf, strlen(s_receipt_buf));
            return rc == 0 ? 0 : BLE_ATT_ERR_INSUFFICIENT_RES;
        }
        return BLE_ATT_ERR_UNLIKELY;
    }

    if (attr_handle == s_invoke_val_handle) {
        if (ctxt->op == BLE_GATT_ACCESS_OP_WRITE_CHR) {
            uint16_t len = 0;
            char in_buf[MAX_PAYLOAD_LEN];
            rc = ble_hs_mbuf_to_flat(ctxt->om, in_buf, sizeof(in_buf) - 1, &len);
            if (rc != 0) {
                ESP_LOGE(TAG, "Failed to read incoming invocation mbuf: %d", rc);
                return BLE_ATT_ERR_UNLIKELY;
            }
            in_buf[len] = '\0';
            ESP_LOGI(TAG, "Received BLE invocation (%d bytes)", len);

            // Pass completely to protocol layer
            capmesh_dispatcher_handle_request(in_buf, s_receipt_buf, sizeof(s_receipt_buf));

            // Notify connected client that receipt is ready
            ble_gatts_chr_updated(s_receipt_val_handle);
            return 0;
        }
        return BLE_ATT_ERR_UNLIKELY;
    }

    return BLE_ATT_ERR_UNLIKELY;
}

static void ble_advertise(void);

static int ble_gap_event(struct ble_gap_event *event, void *arg)
{
    switch (event->type) {
    case BLE_GAP_EVENT_CONNECT:
        ESP_LOGI(TAG, "BLE client connection %s; status=%d",
                 event->connect.status == 0 ? "established" : "failed",
                 event->connect.status);
        if (event->connect.status != 0) {
            ble_advertise();
        }
        return 0;

    case BLE_GAP_EVENT_DISCONNECT:
        ESP_LOGI(TAG, "BLE client disconnected; reason=%d", event->disconnect.reason);
        ble_advertise();
        return 0;

    case BLE_GAP_EVENT_ADV_COMPLETE:
        ESP_LOGI(TAG, "BLE advertising complete; restarting");
        ble_advertise();
        return 0;

    case BLE_GAP_EVENT_SUBSCRIBE:
        ESP_LOGI(TAG, "BLE subscribe event; attr_handle=%d, cur_notify=%d",
                 event->subscribe.attr_handle, event->subscribe.cur_notify);
        return 0;

    case BLE_GAP_EVENT_MTU:
        ESP_LOGI(TAG, "BLE MTU updated to: %d bytes (conn_handle=%d)",
                 event->mtu.value, event->mtu.conn_handle);
        return 0;

    default:
        return 0;
    }
}

static void ble_advertise(void)
{
    struct ble_gap_adv_params adv_params;
    struct ble_hs_adv_fields fields;
    int rc;

    memset(&fields, 0, sizeof(fields));
    fields.flags = BLE_HS_ADV_F_DISC_GEN | BLE_HS_ADV_F_BREDR_UNSUP;
    fields.tx_pwr_lvl_is_present = 1;
    fields.tx_pwr_lvl = BLE_HS_ADV_TX_PWR_LVL_AUTO;

    fields.name = (uint8_t *)s_device_name;
    fields.name_len = strlen(s_device_name);
    fields.name_is_complete = 1;

    fields.uuids16 = (ble_uuid16_t[]){ s_svc_uuid };
    fields.num_uuids16 = 1;
    fields.uuids16_is_complete = 1;

    rc = ble_gap_adv_set_fields(&fields);
    if (rc != 0) {
        ESP_LOGE(TAG, "Error setting advertisement data; rc = %d", rc);
        return;
    }

    memset(&adv_params, 0, sizeof(adv_params));
    adv_params.conn_mode = BLE_GAP_CONN_MODE_UND;
    adv_params.disc_mode = BLE_GAP_DISC_MODE_GEN;
    adv_params.itvl_min = BLE_GAP_ADV_FAST_INTERVAL1_MIN;
    adv_params.itvl_max = BLE_GAP_ADV_FAST_INTERVAL1_MAX;

    rc = ble_gap_adv_start(s_own_addr_type, NULL, BLE_HS_FOREVER,
                           &adv_params, ble_gap_event, NULL);
    if (rc != 0) {
        ESP_LOGE(TAG, "Error starting advertising; rc = %d", rc);
        return;
    }
    ESP_LOGI(TAG, "BLE advertising started as '%s' (UUID: 0xCB00)", s_device_name);
}

static void ble_on_sync(void)
{
    int rc = ble_hs_util_ensure_addr(0);
    if (rc != 0) {
        ESP_LOGE(TAG, "Failed to ensure identity address; rc = %d", rc);
        return;
    }

    rc = ble_hs_id_infer_auto(0, &s_own_addr_type);
    if (rc != 0) {
        ESP_LOGE(TAG, "Failed to determine address type; rc = %d", rc);
        return;
    }

    uint8_t addr[6];
    rc = ble_hs_id_copy_addr(s_own_addr_type, addr, NULL);
    if (rc == 0) {
        ESP_LOGI(TAG, "BLE MAC: %02x:%02x:%02x:%02x:%02x:%02x",
                 addr[5], addr[4], addr[3], addr[2], addr[1], addr[0]);
    }

    ble_advertise();
}

static void ble_on_reset(int reason)
{
    ESP_LOGE(TAG, "NimBLE host reset; reason = %d", reason);
}

static void ble_host_task(void *param)
{
    ESP_LOGI(TAG, "NimBLE host task started");
    nimble_port_run();
    nimble_port_freertos_deinit();
}

esp_err_t capmesh_ble_transport_init(const char *device_name)
{
    if (device_name && strlen(device_name) > 0) {
        strncpy(s_device_name, device_name, sizeof(s_device_name) - 1);
        s_device_name[sizeof(s_device_name) - 1] = '\0';
    }

    // Pre-populate manifest
    capmesh_dispatcher_get_manifest(s_manifest_buf, sizeof(s_manifest_buf));

    esp_err_t ret = nimble_port_init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize NimBLE port: %d", ret);
        return ret;
    }

    ble_hs_cfg.reset_cb = ble_on_reset;
    ble_hs_cfg.sync_cb = ble_on_sync;

    ret = ble_svc_gap_device_name_set(s_device_name);
    if (ret != 0) {
        ESP_LOGE(TAG, "Failed to set device name: %d", ret);
        return ESP_FAIL;
    }

    ble_svc_gap_init();
    ble_svc_gatt_init();

    int rc = ble_gatts_count_cfg(s_gatt_svcs);
    if (rc != 0) {
        ESP_LOGE(TAG, "Failed to count GATT services: %d", rc);
        return ESP_FAIL;
    }

    rc = ble_gatts_add_svcs(s_gatt_svcs);
    if (rc != 0) {
        ESP_LOGE(TAG, "Failed to add GATT services: %d", rc);
        return ESP_FAIL;
    }

    nimble_port_freertos_init(ble_host_task);
    ESP_LOGI(TAG, "NimBLE initialized successfully");
    return ESP_OK;
}
