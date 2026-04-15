#include "camera.h"

#include "esp_camera.h"
#include "esp_log.h"
#include "bsp/esp-bsp.h"

#define TAG "CAMERA"


esp_err_t camera_setup()
{
    bsp_camera_start(NULL);
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