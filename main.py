#!/usr/bin/env python3
import asyncio
import time
from datetime import datetime
import os
import sys
import json
from mqtt_client import MQTT_Hassio
from tydom_websocket import TydomWebSocketClient

############ HASSIO ADDON

print('STARTING MAIN LOOP TYDOM2MQTT')

print('Dectecting environnement......')
try:
    with open('/data/options.json') as f:
        print('/data/options.json detected ! Hassio Addons Environnement : parsing options.json....')
        try:
            data = json.load(f)
            print(data)
            ####### CREDENTIALS TYDOM
            TYDOM_MAC = data['TYDOM_MAC'] #MAC Address of Tydom Box
            if data['TYDOM_IP'] != '':
                TYDOM_IP = data['TYDOM_IP'] #, 'mediation.tydom.com') # Local ip address, default to mediation.tydom.com for remote connexion if not specified
            else:
                TYDOM_IP = 'mediation.tydom.com'
            TYDOM_PASSWORD = data['TYDOM_PASSWORD'] #Tydom password

            ####### CREDENTIALS MQTT
            if data['MQTT_HOST'] != '':
                MQTT_HOST = data['MQTT_HOST'] #, 'mediation.tydom.com') # Local ip address, default to mediation.tydom.com for remote connexion if not specified
            else:
                MQTT_HOST = 'localhost'
            
            MQTT_USER = data['MQTT_USER']
            MQTT_PASSWORD = data['MQTT_PASSWORD']

        except Exception as e:
            print('Parsing error', e)

except FileNotFoundError :
    print("No /data/options.json, seems where are not in hassio addon mode.")
    ####### CREDENTIALS TYDOM
    TYDOM_MAC = os.getenv('TYDOM_MAC') #MAC Address of Tydom Box
    TYDOM_IP = os.getenv('TYDOM_IP', 'mediation.tydom.com') # Local ip address, default to mediation.tydom.com for remote connexion if not specified
    TYDOM_PASSWORD = os.getenv('TYDOM_PASSWORD') #Tydom password

    ####### CREDENTIALS MQTT
    MQTT_HOST = os.getenv('MQTT_HOST', 'localhost')
    MQTT_USER = os.getenv('MQTT_USER')
    MQTT_PASSWORD = os.getenv('MQTT_PASSWORD')

loop = asyncio.get_event_loop()

def loop_task():
    print('Starting loop_task')
    tydom = None
    hassio = None

    if (MQTT_HOST == 'localhost'):
        MQTT_PORT = 1883 #1884 for websocket without SSL
        MQTT_SSL = False
    else:
        MQTT_PORT = 8883 #8884 for websocket
        MQTT_SSL = True

    # Creating client object
    hassio = MQTT_Hassio(MQTT_HOST, MQTT_PORT, MQTT_USER, MQTT_PASSWORD, MQTT_SSL)
    # hassio_connection = loop.run_until_complete(hassio.connect())
    # Giving MQTT connection to tydom class for updating
    tydom = TydomWebSocketClient(mac=TYDOM_MAC, host=TYDOM_IP, password=TYDOM_PASSWORD, mqtt_client=hassio)

    # Start connection and get client connection protocol
    loop.run_until_complete(tydom.mqtt_client.connect())

    loop.run_until_complete(tydom.connect())
    # Giving back tydom client to MQTT client
    hassio.tydom = tydom
    print('Broker and Tydom Websocket READY')
    print('Start websocket listener and heartbeat')

    tasks = [
        tydom.receiveMessage(),
        tydom.heartbeat()
    ]

    loop.run_until_complete(asyncio.wait(tasks))
    # loop.run_forever()

if __name__ == '__main__':

    try:
        loop_task()
    except Exception as e:
        error = "FATAL ERROR ! {}".format(e)
        print(error)