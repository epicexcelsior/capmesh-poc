#include "transport/http_transport.h"
#include "protocol/capmesh_dispatcher.h"
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include <string.h>

static const char *TAG = "HTTP_TRANS";

static httpd_handle_t s_server = NULL;
static char s_last_receipt[1024] = "{\"protocol\":\"capmesh/0.1\",\"status\":\"idle\"}";

static esp_err_t manifest_handler(httpd_req_t *req)
{
    char buf[1024];
    int len = capmesh_dispatcher_get_manifest(buf, sizeof(buf));
    if (len < 0) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, buf, len);
}

static esp_err_t invoke_handler(httpd_req_t *req)
{
    char in_buf[1024];
    int total_len = req->content_len;
    if (total_len >= (int)sizeof(in_buf)) {
        httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Payload too large");
        return ESP_FAIL;
    }

    int received = httpd_req_recv(req, in_buf, total_len);
    if (received <= 0) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }
    in_buf[received] = '\0';

    ESP_LOGI(TAG, "Received HTTP invocation: %s", in_buf);

    int out_len = capmesh_dispatcher_handle_request(in_buf, s_last_receipt, sizeof(s_last_receipt));
    if (out_len < 0) {
        httpd_resp_send_500(req);
        return ESP_FAIL;
    }

    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, s_last_receipt, out_len);
}

static esp_err_t receipt_handler(httpd_req_t *req)
{
    httpd_resp_set_type(req, "application/json");
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    return httpd_resp_send(req, s_last_receipt, strlen(s_last_receipt));
}

esp_err_t capmesh_http_transport_init(const char *ap_ssid)
{
    ESP_LOGI(TAG, "Initializing Wi-Fi SoftAP and HTTP transport...");

    // Wi-Fi Netif & Event loop
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    esp_err_t ret = esp_wifi_init(&cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "esp_wifi_init failed: %d", ret);
        return ret;
    }

    wifi_config_t wifi_config = {
        .ap = {
            .ssid_len = strlen(ap_ssid),
            .channel = 6,
            .authmode = WIFI_AUTH_OPEN,
            .max_connection = 4,
            .beacon_interval = 100,
        },
    };
    strncpy((char *)wifi_config.ap.ssid, ap_ssid, sizeof(wifi_config.ap.ssid));

    ret = esp_wifi_set_mode(WIFI_MODE_AP);
    if (ret != ESP_OK) return ret;
    ret = esp_wifi_set_config(WIFI_IF_AP, &wifi_config);
    if (ret != ESP_OK) return ret;
    ret = esp_wifi_start();
    if (ret != ESP_OK) return ret;

    ESP_LOGI(TAG, "Wi-Fi SoftAP started with SSID '%s' on channel 6", ap_ssid);

    // Embedded HTTP Server
    httpd_config_t http_cfg = HTTPD_DEFAULT_CONFIG();
    http_cfg.max_uri_handlers = 8;
    http_cfg.stack_size = 8192;

    ret = httpd_start(&s_server, &http_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start HTTP server: %d", ret);
        return ret;
    }

    httpd_uri_t uri_manifest = {
        .uri = "/manifest",
        .method = HTTP_GET,
        .handler = manifest_handler,
        .user_ctx = NULL
    };
    httpd_uri_t uri_invoke = {
        .uri = "/invoke",
        .method = HTTP_POST,
        .handler = invoke_handler,
        .user_ctx = NULL
    };
    httpd_uri_t uri_receipt = {
        .uri = "/receipt",
        .method = HTTP_GET,
        .handler = receipt_handler,
        .user_ctx = NULL
    };

    httpd_register_uri_handler(s_server, &uri_manifest);
    httpd_register_uri_handler(s_server, &uri_invoke);
    httpd_register_uri_handler(s_server, &uri_receipt);

    ESP_LOGI(TAG, "CapMesh HTTP transport listening on http://192.168.4.1/ (endpoints: /manifest, /invoke, /receipt)");
    return ESP_OK;
}
