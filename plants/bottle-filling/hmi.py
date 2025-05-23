#!/usr/bin/env python

import sys
import tkinter as tk
from modbus import ClientModbus as Client
from modbus import ConnectionException
import os
import time
import json
import argparse

from world import PLC_RW_ADDR, PLC_RO_ADDR, PLC_TAG_CONTACT, PLC_TAG_LEVEL, PLC_TAG_MOTOR, PLC_TAG_NOZZLE, PLC_TAG_RUN

# Constants
HMI_SCREEN_WIDTH = 20
HMI_SLEEP = 1

class HMIWindow:
    def resetLabels(self):
        self.bottlePositionValue.config(text="N/A", fg="gray33")
        self.motorStatusValue.config(text="N/A", fg="gray33")
        self.levelHitValue.config(text="N/A", fg="gray33")
        self.processStatusValue.config(text="N/A", fg="gray33")
        self.nozzleStatusValue.config(text="N/A", fg="gray33")
        self.connectionStatusValue.config(text="OFFLINE", fg="red")

    def __init__(self, address, base_port):
        ports = {
            "plc": base_port
        }
        if os.path.exists("ports.json"):
            with open("ports.json", "r") as f:
                saved_ports = json.load(f)
            if saved_ports.get("plc") == base_port:
                ports = saved_ports

        self.client = Client(address, port=ports["plc"])
        self.client.connect()

        self.window = tk.Tk()
        self.window.title("Bottle-filling factory - HMI - VirtuaPlant")

        self.frame = tk.Frame(self.window)
        self.frame.pack(padx=HMI_SCREEN_WIDTH, pady=HMI_SCREEN_WIDTH)

        self.create_widgets()
        self.window.after(HMI_SLEEP * 1000, self.update_status)

    def create_widgets(self):
        label = tk.Label(self.frame, text="Bottle-filling process status", font=("Helvetica", 16, "bold"))
        label.grid(row=0, column=0, columnspan=2)

        self.bottlePositionLabel = tk.Label(self.frame, text="Bottle in position")
        self.bottlePositionValue = tk.Label(self.frame, text="N/A", fg="gray33")
        self.bottlePositionLabel.grid(row=1, column=0)
        self.bottlePositionValue.grid(row=1, column=1)

        self.nozzleStatusLabel = tk.Label(self.frame, text="Nozzle Status")
        self.nozzleStatusValue = tk.Label(self.frame, text="N/A", fg="gray33")
        self.nozzleStatusLabel.grid(row=2, column=0)
        self.nozzleStatusValue.grid(row=2, column=1)

        self.motorStatusLabel = tk.Label(self.frame, text="Motor Status")
        self.motorStatusValue = tk.Label(self.frame, text="N/A", fg="gray33")
        self.motorStatusLabel.grid(row=3, column=0)
        self.motorStatusValue.grid(row=3, column=1)

        self.levelHitLabel = tk.Label(self.frame, text="Level Hit")
        self.levelHitValue = tk.Label(self.frame, text="N/A", fg="gray33")
        self.levelHitLabel.grid(row=4, column=0)
        self.levelHitValue.grid(row=4, column=1)

        self.processStatusLabel = tk.Label(self.frame, text="Process Status")
        self.processStatusValue = tk.Label(self.frame, text="N/A", fg="gray33")
        self.processStatusLabel.grid(row=5, column=0)
        self.processStatusValue.grid(row=5, column=1)

        self.connectionStatusLabel = tk.Label(self.frame, text="Connection Status")
        self.connectionStatusValue = tk.Label(self.frame, text="OFFLINE", fg="red")
        self.connectionStatusLabel.grid(row=6, column=0)
        self.connectionStatusValue.grid(row=6, column=1)

        self.runButton = tk.Button(self.frame, text="Run", command=lambda: self.setProcess(1))
        self.stopButton = tk.Button(self.frame, text="Stop", command=lambda: self.setProcess(0))
        self.runButton.grid(row=7, column=0)
        self.stopButton.grid(row=7, column=1)

        self.virtuaPlantLabel = tk.Label(self.frame, text="VirtuaPlant - HMI", font=("Helvetica", 8, "italic"))
        self.virtuaPlantLabel.grid(row=8, column=0, columnspan=2)

    def setProcess(self, data=None):
        try:
            self.client.write(PLC_RW_ADDR + PLC_TAG_RUN, data)
        except:
            pass

    def update_status(self):
        try:
            regs = self.client.readln(PLC_RO_ADDR, 17)

            self.bottlePositionValue.config(
                text="YES" if regs[PLC_TAG_CONTACT] == 1 else "NO",
                fg="green" if regs[PLC_TAG_CONTACT] == 1 else "red"
            )

            self.levelHitValue.config(
                text="YES" if regs[PLC_TAG_LEVEL] == 1 else "NO",
                fg="green" if regs[PLC_TAG_LEVEL] == 1 else "red"
            )

            self.motorStatusValue.config(
                text="ON" if regs[PLC_TAG_MOTOR] == 1 else "OFF",
                fg="green" if regs[PLC_TAG_MOTOR] == 1 else "red"
            )

            self.nozzleStatusValue.config(
                text="OPEN" if regs[PLC_TAG_NOZZLE] == 1 else "CLOSED",
                fg="green" if regs[PLC_TAG_NOZZLE] == 1 else "red"
            )

            regs_rw = self.client.readln(PLC_RW_ADDR, 17)

            self.processStatusValue.config(
                text="RUNNING" if regs_rw[PLC_TAG_RUN] == 1 else "STOPPED",
                fg="green" if regs_rw[PLC_TAG_RUN] == 1 else "red"
            )

            self.connectionStatusValue.config(text="ONLINE", fg="green")

        except ConnectionException:
            if not self.client.connect():
                self.resetLabels()
        except:
            raise
        finally:
            self.window.after(HMI_SLEEP * 1000, self.update_status)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Launched the HMI for Virtuaplant.")
    parser.add_argument("--ip", required=True, help="Server IP address")
    parser.add_argument("--port", type=int, required=True, help="PLC server port")
    return parser.parse_args()

def main():
    args = parse_arguments()
    hmi = HMIWindow(args.ip, args.port)
    hmi.window.mainloop()

if __name__ == "__main__":
    sys.exit(main())
