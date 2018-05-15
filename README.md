# Asysbus component for Home Assistant

Copy the files into `~/.homeassistant/custom_components/` directory and add the configurations blocks to your normal `~/.homeassistant/configuration.yaml`.

## Example configuration for serial bridge

This block must be added on root level of your configuration.

    asysbus:
      serial_port: /dev/ttyACM0
      baudrate: 115200

## Example configuration for switches

These examples must be added to the `switch` block of your configuration.

    - platform: asysbus
      id: 0x07D0
      name: "Asysbus switch 1"

    - platform: asysbus
      id: 0x07D1
      name: "Asysbus switch 2"

## Example configuration for lights

These examples must be added to the `light` block of your configuration.

    - platform: asysbus
      id: 0x03E8
      name: "Asysbus light 1"
      type: "RGB"

    - platform: asysbus
      id: 0x03E9
      name: "Asysbus light 2"
      type: "RGBW"
