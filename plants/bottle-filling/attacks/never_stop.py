import argparse
import logging
import time
import os
import sys
import json
import threading
import contextlib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

with open(os.devnull, 'w') as fnull, contextlib.redirect_stdout(fnull), contextlib.redirect_stderr(fnull):
    from world import (
        PLC_RW_ADDR,
        PLC_TAG_NEVER_STOP
    )

from modbus import ClientModbus as Client
from modbus import ConnectionException

logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.INFO)

parser = argparse.ArgumentParser(description="Activate the 'never_stop' mode from ModBus.")
parser.add_argument('--ip', required=True, help='ModBus server IP address')
parser.add_argument('--port', required=True, help='Modbus server port')
args = parser.parse_args()

PORTS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'ports.json'))

with open(PORTS_FILE, "r") as f:
    ports = json.load(f)

client = Client(args.ip, args.port)
stop_flag = False

def listen_for_enter():
    input("")
    global stop_flag
    stop_flag = True

try:
    client.connect()

    threading.Thread(target=listen_for_enter, daemon=True).start()

    client.write(PLC_RW_ADDR + PLC_TAG_NEVER_STOP, 1)

    while not stop_flag:
        time.sleep(0.01)

    client.write(PLC_RW_ADDR + PLC_TAG_NEVER_STOP, 0)

except Exception as e:
    log.error(f"Connection or writing error: {e}")
