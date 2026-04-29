#include "camera.h"

#include "esp_camera.h"
#include "esp_log.h"
#include "bsp/esp-bsp.h"

#define TAG "CAMERA"


esp_err_t camera_setup()
{
    bsp_i2c_init();
    camera_config_t camera_config = BSP_CAMERA_DEFAULT_CONFIG;
    camera_config.fb_count = 1;
    camera_config.grab_mode = CAMERA_GRAB_LATEST;  
    
    esp_err_t err = esp_camera_init(&camera_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Camera Init Failed");
        return ESP_FAIL;
    }
    ESP_LOGI(TAG, "CAMERA SETUP OK");
    return ESP_OK;
}

esp_err_t camera_capture(void (*process_image)(camera_fb_t *fb))
{
    
    camera_fb_t * fb = esp_camera_fb_get();
    if (!fb) {
        ESP_LOGE(TAG, "Camera Capture Failed");
        return ESP_FAIL;
    }

    process_image(fb);

    esp_camera_fb_return(fb);
    return ESP_OK;
}