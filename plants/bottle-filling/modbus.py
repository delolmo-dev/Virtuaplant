#!/usr/bin/env python

import sys
from pymodbus.client.sync import ModbusTcpClient
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.exceptions import ConnectionException
from pymodbus.transaction import ModbusSocketFramer

MODBUS_PORT = 2052

class ClientModbus(ModbusTcpClient):    
    def __init__(self, address, port=MODBUS_PORT):
        super().__init__(address, port)

    def read(self, addr):
        try:
            regs = self.readln(addr, 1)
            return regs[0]
        except ConnectionException:
            self.connect()
            regs = self.readln(addr, 1)
            return regs[0]

    def readln(self, addr, size):
        rr = self.read_holding_registers(addr, size)
        if not rr or not hasattr(rr, 'registers'):
            raise ConnectionException
        if len(rr.registers) < size:
            raise ConnectionException
        return rr.registers

    def write(self, addr, data):
        self.write_register(addr, data)

    def writeln(self, addr, data, size):
        self.write_registers(addr, data)

class ServerModbus:
    def __init__(self, address="localhost", port=MODBUS_PORT):
        self.address = address
        self.port = port
        self.block = ModbusSequentialDataBlock(0x00, [0]*0x3ff)
        store = ModbusSlaveContext(di=self.block, co=self.block, hr=self.block, ir=self.block)
        self.context = ModbusServerContext(slaves=store, single=True)
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = 'MockPLCs'
        self.identity.ProductCode = 'MP'
        self.identity.VendorUrl = 'http://github.com/bashwork/pyddmodbus/'
        self.identity.ProductName = 'MockPLC 3000'
        self.identity.ModelName = 'MockPLC Ultimate'
        self.identity.MajorMinorRevision = '1.0'

    def read(self, addr):
        return self.context[0].getValues(3, addr, count=1)[0]

    def write(self, addr, value):
        self.context[0].setValues(3, addr, [value])

    def start(self):
        StartTcpServer(context=self.context, identity=self.identity, address=(self.address, self.port))

def main():
    print("Modbus TCP ready.")
    server = ServerModbus()
    server.start()
    return 0

if __name__ == "__main__":
    sys.exit(main())
