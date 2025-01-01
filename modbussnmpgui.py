import tkinter as tk
from tkinter import messagebox, filedialog
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext, ModbusSequentialDataBlock
from pymodbus.server.sync import StartTcpServer
from pymodbus.device import ModbusDeviceIdentification
import socket
import threading
from pysnmp.hlapi import *
import json
import time
import sys

# Función para redirigir la salida de la consola a la interfaz gráfica
class ConsoleRedirect:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, message):
        self.text_widget.insert(tk.END, message)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

# Función para realizar la consulta SNMP
def get_snmp_value(target, community, oid, portSnmp):
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(community, mpModel=0),  # Utilizar SNMPv1 (mpModel=0)
               UdpTransportTarget((target, portSnmp)),
               ContextData(),
               ObjectType(ObjectIdentity(oid)))
    )
    if errorIndication:
        print(f"Error al obtener el valor del OID {oid}: {errorIndication}")
    elif errorStatus:
        print(f"Error en la respuesta SNMP para el OID {oid}: {errorStatus.prettyPrint()}")
    else:
        for varBind in varBinds:
            return varBind[1]

# Función para cargar los OID desde un archivo JSON
def load_oid_from_json(filename):
    try:
        with open(filename, 'r') as file:
            data = json.load(file)
            return [data[key].strip() for key in data]
    except Exception as e:
        print(f"Error al cargar el archivo JSON {filename}: {e}")
        return []

# Configuración inicial
filename = 'OID.json'
oid_list = load_oid_from_json(filename)

# Función para cargar un archivo desde la interfaz gráfica
def cargar_archivo():
    global filename, oid_list
    archivo = filedialog.askopenfilename(filetypes=[("Archivos JSON", "*.json")])
    if archivo:
        filename = archivo
        oid_list = load_oid_from_json(filename)
        messagebox.showinfo("Archivo Cargado", f"Archivo cargado correctamente: {archivo}")
        print(oid_list)
    else:
        messagebox.showwarning("Carga Cancelada", "No se seleccionó ningún archivo.")

# Interfaz gráfica para configurar los parámetros SNMP
def iniciar():
    target_ip = target_ip_entry.get()
    community = community_entry.get()
    portSnmpStr = portSnmp_entry.get() 
    portModbusStr = portModbus_entry.get()
    slaveModbusStr = slaveModbus_entry.get()
    slaveModbus =  int(slaveModbusStr)
    portSnmp =  int(portSnmpStr)
    portModbus =  int(portModbusStr)

    if not all([target_ip, community, portSnmp, portModbus, slaveModbus]):
        messagebox.showerror("Error", "Todos los campos son obligatorios.")
        return

    iniciar_modbus_snmp(target_ip, community, portSnmp, portModbus, slaveModbus)

def iniciar_modbus_snmp(target_ip, community, portSnmp, portModbus, slaveModbus):
    # Configuración de Modbus
    registroInicial = 1

    store = ModbusSlaveContext(
        di=ModbusSequentialDataBlock(0, [0] * 3000),
        co=ModbusSequentialDataBlock(0, [0] * 3000),
        hr=ModbusSequentialDataBlock(registroInicial, [0] * 1000),
        ir=ModbusSequentialDataBlock(0, [0] * 3000)
    )

    context = ModbusServerContext(slaves={slaveModbus: store}, single=False)

    identity = ModbusDeviceIdentification()
    identity.VendorName = 'Camilo Vanegas'
    identity.ProductCode = '9210'
    identity.ProductName = 'Modbus Slave'

    local_ip = extract_ip()

    server_thread = threading.Thread(target=StartTcpServer, args=(context, identity), kwargs={'address': (local_ip, portModbus)})
    server_thread.start()

    def update_registers():
        while True:
            registro = registroInicial

            for oid in oid_list:
                dato = get_snmp_value(target_ip, community, oid, portSnmp)
                store.setValues(3, registro, [dato])
                print(f"Dispositivo 1 - Registro {registro}: {dato}")
                registro += 1

            print("Valores actualizados. Esperando 1 minuto...")
            time.sleep(60)

    update_thread = threading.Thread(target=update_registers)
    update_thread.start()

def extract_ip():
    st = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        st.connect(("10.255.255.255", 1))
        IP = st.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        st.close()
    return IP

ip_pc = extract_ip()
title = "ModbusTCP" + " " + ip_pc

# Crear ventana principal
root = tk.Tk()
root.title(title)

# Campos de entrada
tk.Label(root, text="IP SNMP:").grid(row=0, column=0)
target_ip_entry = tk.Entry(root)
target_ip_entry.grid(row=0, column=1)

tk.Label(root, text="Community SNMP:").grid(row=3, column=0)
community_entry = tk.Entry(root)
community_entry.grid(row=3, column=1)

tk.Label(root, text="Port SNMP (default 161):").grid(row=6, column=0)
portSnmp_entry = tk.Entry(root)
portSnmp_entry.grid(row=6, column=1)

tk.Label(root, text="Port Modbus (default 502):").grid(row=9, column=0)
portModbus_entry = tk.Entry(root)
portModbus_entry.grid(row=9, column=1)

tk.Label(root, text="Slave Modbus:").grid(row=12, column=0)
slaveModbus_entry = tk.Entry(root)
slaveModbus_entry.grid(row=12, column=1)

# Botón para cargar archivo
load_button = tk.Button(root, text="Cargar Archivo OID", command=cargar_archivo)
load_button.grid(row=13, column=0, columnspan=2)

# Botón para iniciar
start_button = tk.Button(root, text="Iniciar ModbusTCP", command=iniciar)
start_button.grid(row=14, column=0, columnspan=2)

# Área de salida de consola
tk.Label(root, text="Salida de Consola:").grid(row=15, column=0, columnspan=2)
console_output = tk.Text(root, height=15, width=50)
console_output.grid(row=16, column=0, columnspan=2)

# Redirigir la salida estándar a la consola de la interfaz gráfica
sys.stdout = ConsoleRedirect(console_output)
sys.stderr = ConsoleRedirect(console_output)

root.mainloop()
