
build:
	pio run

flash:
	pio run --target upload --upload-port /dev/ttyUSB0

debug:
	@echo Use CTRL+T , CTRL+R to release reset line and start the target
	pio device monitor

.PHONY: build flash debug
