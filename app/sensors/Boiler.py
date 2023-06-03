import json
import logging

logger = logging.getLogger(__name__)
climate_config_topic = "homeassistant/climate/tydom/{id}/config"
sensor_config_topic = "homeassistant/sensor/tydom/{id}/config"
climate_json_attributes_topic = "climate/tydom/{id}/state"

temperature_command_topic = "climate/tydom/{id}/set_setpoint"
temperature_state_topic = "climate/tydom/{id}/setpoint"
current_temperature_topic = "climate/tydom/{id}/temperature"
mode_state_topic = "climate/tydom/{id}/hvacMode"
mode_command_topic = "climate/tydom/{id}/set_hvacMode"
preset_mode_state_topic = "climate/tydom/{id}/authorization"
preset_mode_command_topic = "climate/tydom/{id}/set_authorization"
out_temperature_state_topic = "sensor/tydom/{id}/temperature"

#temperature = current_temperature_topic
#setpoint= temperature_command_topic
# temperature_unit=C
# "modes": ["STOP", "ANTI-FROST","ECO", "COMFORT"],
#####################################
# setpoint (seulement si thermostat)
# temperature (intérieure, seulement si thermostat)
# anticipCoeff 30 (seulement si thermostat)

# thermicLevel STOP ECO ...
# auhorisation HEATING
# hvacMode NORMAL None (si off)
#timeDelay : 0
#tempoOn : False
# antifrost True False
# openingdetected False
# presenceDetected False
# absence False
# LoadSheddingOn False

# outTemperature float
##################################

# climate_json_attributes_topic = "climate/tydom/{id}/state"
# State topic can be the same as the original device attributes topic !


class Boiler:

    def __init__(self, tydom_attributes, tydom_client=None, mqtt=None):

        self.config_topic = None
        self.topic_to_func = None
        self.config = None
        self.device = None
        self.attributes = tydom_attributes
        self.device_id = self.attributes['device_id']
        self.endpoint_id = self.attributes['endpoint_id']
        self.id = self.attributes['id']
        self.name = self.attributes['name']
        self.mqtt = mqtt
        self.tydom_client = tydom_client

    async def setup(self):
        self.config = {}
        self.device = {
            'manufacturer': 'Delta Dore',
            'name': self.name,
            'identifiers': self.id}

        # Check if device is an outer temperature sensor
        if 'outTemperature' in self.attributes:
            self.config['name'] = 'Out Temperature'
            self.device['model'] = 'Sensor'
            self.config['device_class'] = 'temperature'
            self.config['unit_of_measurement'] = 'C'
            self.config_topic = sensor_config_topic.format(id=self.id)
            self.config['state_topic'] = out_temperature_state_topic.format(
                id=self.id)
            self.topic_to_func = {}

        # Check if device is a heater with thermostat sensor
        else:
            self.config['name'] = self.name
            self.device['model'] = 'Climate'
            self.config_topic = climate_config_topic.format(id=self.id)
            self.config['temperature_command_topic'] = temperature_command_topic.format(
                id=self.id)
            self.config['temperature_state_topic'] = temperature_state_topic.format(
                id=self.id)
            self.config['current_temperature_topic'] = current_temperature_topic.format(
                id=self.id)
            self.config['modes'] = ["off", "heat", "cool"]
            self.config['mode_state_topic'] = mode_state_topic.format(
                id=self.id)
            self.config['mode_command_topic'] = mode_command_topic.format(
                id=self.id)
            self.config['preset_modes'] = [
                "STOP", "HEATING", "COOLING"]
            self.config['preset_mode_state_topic'] = preset_mode_state_topic.format(
                id=self.id)
            self.config['preset_mode_command_topic'] = preset_mode_command_topic.format(
                id=self.id)

        self.config['unique_id'] = self.id

        if self.mqtt is not None:
            self.mqtt.mqtt_client.publish(
                self.config_topic, json.dumps(
                    self.config), qos=0, retain=True)

    async def update(self):
        await self.setup()

        if self.mqtt is not None:
            if 'temperature' in self.attributes:
                self.mqtt.mqtt_client.publish(
                    self.config['current_temperature_topic'],
                    '0' if self.attributes['temperature'] == 'None' else self.attributes['temperature'],
                    qos=0, retain=True)
            if 'setpoint' in self.attributes:
                self.mqtt.mqtt_client.publish(
                    self.config['temperature_state_topic'],
                    '10' if self.attributes['setpoint'] == 'None' else self.attributes['setpoint'],
                    qos=0, retain=True)
            if 'authorization' in self.attributes:
                self.mqtt.mqtt_client.publish(
                    self.config['mode_state_topic'],
                    "heat" if self.attributes['authorization'] == "HEATING" else
		    "cool" if self.attributes['authorization'] == "COOLING" else
		    "off",
                    qos=0, retain=True)
                self.mqtt.mqtt_client.publish(
                    self.config['preset_mode_state_topic'],
                    self.attributes['authorization'],
                    qos=0, retain=True)
            if 'outTemperature' in self.attributes:
                self.mqtt.mqtt_client.publish(
                    self.config['state_topic'],
                    self.attributes['outTemperature'],
                    qos=0, retain=True)

    @staticmethod
    async def put_temperature(tydom_client, device_id, boiler_id, set_setpoint):
        logger.info("%s %s %s", boiler_id, 'set_setpoint', set_setpoint)
        if not (set_setpoint == ''):
            await tydom_client.put_devices_data(device_id, boiler_id, 'setpoint', set_setpoint)

    @staticmethod
    async def put_hvac_mode(tydom_client, device_id, boiler_id, set_hvac_mode):
        logger.info("%s %s %s", boiler_id, 'set_hvacMode', set_hvac_mode)
        if set_hvac_mode == 'heat':
            await tydom_client.put_devices_data(device_id, boiler_id, 'authorization', 'HEATING')
        if set_hvac_mode == 'cool':
            await tydom_client.put_devices_data(device_id, boiler_id, 'authorization', 'COOLING')
        else:
            await tydom_client.put_devices_data(device_id, boiler_id, 'setpoint', '00')
            await tydom_client.put_devices_data(device_id, boiler_id, 'thermicLevel', '00')
            await tydom_client.put_devices_data(device_id, boiler_id, 'authorization', 'STOP')           
        #   await tydom_client.put_devices_data(device_id, boiler_id, 'setpoint', '10')

    @staticmethod
    async def put_thermic_level(tydom_client, device_id, boiler_id, set_thermic_level):
        if not (set_thermic_level == ''):
            logger.info("Set thermic level (device=%s, level=%s)", device_id, set_thermic_level)
            await tydom_client.put_devices_data(device_id, boiler_id, 'thermicLevel', set_thermic_level)
