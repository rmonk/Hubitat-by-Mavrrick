.PHONY: all build clean bundle-govee-v2 sync sync-all sync-list

BUILD_DIR := build
GOVEE_V2_DIR := Govee/v2
GOVEE_BUNDLE_DIR := Govee/bundle

all: build

build: bundle-govee-v2

sync:
	python3 scripts/hubitat_sync.py push Govee/v2/Mavrrick.Goveev2ColorLights3Driver.groovy Govee/v2/Mavrrick.GoveeIntegrationv2.groovy

sync-all:
	python3 scripts/hubitat_sync.py push-all

sync-list:
	python3 scripts/hubitat_sync.py list

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
