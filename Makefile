.PHONY: all build clean bundle-govee-v2

BUILD_DIR := build
GOVEE_V2_DIR := Govee/v2
GOVEE_BUNDLE_DIR := Govee/bundle

all: build

build: bundle-govee-v2

bundle-govee-v2:
	@mkdir -p $(BUILD_DIR)/govee-v2-bundle
	@cp $(GOVEE_V2_DIR)/Mavrrick.Govee_Cloud_RGB.groovy $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_V2_DIR)/Mavrrick.Govee_Cloud_API.groovy $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_V2_DIR)/Mavrrick.Govee_Cloud_Level.groovy $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_V2_DIR)/Mavrrick.Govee_Cloud_MQTT.groovy $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_V2_DIR)/Mavrrick.Govee_LAN_API.groovy $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_V2_DIR)/Mavrrick.Govee_Cloud_Life.groovy $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_BUNDLE_DIR)/install.txt $(BUILD_DIR)/govee-v2-bundle/
	@cp $(GOVEE_BUNDLE_DIR)/update.txt $(BUILD_DIR)/govee-v2-bundle/
	@rm -f $(BUILD_DIR)/Govee_Integration_v2.zip
	@cd $(BUILD_DIR)/govee-v2-bundle && zip -q -r ../Govee_Integration_v2.zip .
	@echo "Built $(BUILD_DIR)/Govee_Integration_v2.zip"

clean:
	@rm -rf $(BUILD_DIR)
