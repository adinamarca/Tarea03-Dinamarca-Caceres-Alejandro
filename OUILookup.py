import getopt
import sys
import time
import subprocess
import re
    
# Redes
RED_HOST = "192.168.1.30"
MASK = "255.255.255.0"
# Operación entre RED_HOST y MASK (AND por cada octeto)
NET_ID = ".".join([str(i & j) for i, j in zip(map(int, RED_HOST.split(".")), map(int, MASK.split(".")))])
# Strings de respuesta
MISMA_RED = "MAC address: {mac}\nFabricante: {manufacturer}\n"
OTRA_RED = "Error: ip is outside the host network\n"
MAC_EN_BASE_DE_DATOS = "MAC address: {mac}\nFabricante: {manufacturer}\n"
AYUDA = """Use: ./OUILookup --ip <IP> | --mac <IP> | --arp | [--help]
--ip : IP del host a consultar.
--mac: MAC a consultar. P.e. aa:bb:cc:00:00:00.
--arp: muestra los fabricantes de los host
disponibles en la tabla arp.
--help: muestra este mensaje y termina."""

# Api key
def obtiene_api_key():
    """
    Obtiene la api key de un archivo json.
    
    Retorna:
        Api key.
    """
    from json import load
    with open("credentials.json", "r") as file:
        data = load(file)
    return data

def valida_mac(mac: str) -> str:
    """
    Valida una dirección MAC.
    
    Parámetros:
        mac (str): MAC a validar.
        
    Retorna:
        True si la MAC es válida, False en caso contrario.
    """
    # Expresión regular para validar MAC
    if re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower()):
        return True
    else:
        return False

def obtener_fabricante_mac(mac: str) -> str:
    """
    Obtiene el fabricante de una tarjeta de red por MAC.
    
    Parámetros:
        mac (str): MAC del host a consultar.
        
    Retorna:
        Fabricante de la tarjeta de red o "Not found" si no se encuentra.
    """
    from json import loads
    from http import client
    start = time.time()
    conn = client.HTTPSConnection("api.maclookup.app")
    conn.request("GET", "/v2/macs/" + mac + f"?apiKey={obtiene_api_key()['apiKey']}")
    response = conn.getresponse()
    end = time.time()
    time_elapsed = round((end - start)*1000, 3)
    if response.status == 200:
        data: dict = loads(response.read())
        if data["found"] == False:
            return {"data": "Not found", "time(ms)": time_elapsed}
        return {"data": data["company"], "time(ms)": time_elapsed}
    else:
        return {"data": "Not found", "time(ms)": time_elapsed}

def pertenece_a_red(ip: str) -> bool:
    """
    Verifica si una IP pertenece a la red del host.

    Parámetros:
        ip (str): IP a verificar.

    Retorna:
        True si la IP pertenece a la red del host, False en caso contrario.
    """
    # Operación entre IP y MASK (AND por cada octeto)
    ip_net_id = ".".join([str(i & j) for i, j in zip(map(int, ip.split(".")), map(int, MASK.split(".")))])
    return ip_net_id == NET_ID

# Función para obtener los datos de fabricación de una tarjeta de red por IP
def obtener_datos_por_ip(ip: str) -> str:
    """
    Obtiene los datos de fabricación de una tarjeta de red por IP.
    
    Parámetros:
        ip : IP del host a consultar.
    
    Retorna:
        Datos de fabricación de la tarjeta de red o "Not found" si no se encuentra.
    """
    mac = obtener_mac_por_ip(ip)
    if mac == "Not found":
        return "Not found"
    return obtener_fabricante_mac(mac)["data"]
    
def obtener_mac_por_ip(ip: str) -> str:
    """
    Obtiene la MAC de una tarjeta de red por IP.

    Parámetros:
        ip (str): IP del host a consultar.

    Retorna:
        MAC de la tarjeta de red o "Not found" si no se encuentra.
    """
    for fila in obtener_tabla_arp().split("\n"):
        if ip in fila:
            return fila.split("/")[1].strip()
    return "Not found"

# Función para obtener la tabla ARP
def obtener_tabla_arp():
    """
    Obtiene la tabla ARP.
    
    Retorna:
        Texto con la tabla ARP.
    """
    tabla_arp = f"IP\t\t/\tMAC\t\t\t/\tVENDOR\n"
    # Solo nos quedamos con las filas que tienen 4 elementos (IP, tipo, dirección MAC y tipo de interfaz)
    tabla_arp_so = [fila.split(" ")[0:4] for fila in subprocess.check_output(["arp", "-a"]).decode("latin-1").split("\n")]
    tabla_arp_so = [fila for fila in tabla_arp_so if len(fila) == 4]
    for fila in tabla_arp_so:
        # Si la MAC no está vacía, se agrega a la tabla (ya que si está vacía, no se conoce la MAC y por ende aún no se ha hecho ARP)
        if valida_mac(fila[3]):
            ip = fila[1].removeprefix('(').removesuffix(')')
            mac = fila[3]
            fabricante = obtener_fabricante_mac(mac)["data"]
            tabla_arp += f"{ip}\t/\t{mac}\t/\t{fabricante}\n"
    return tabla_arp

def main(argv):

    try:
        opts, args = getopt.getopt(argv, "i:", ["ip=", "mac=", "arp", "help"])

    except getopt.GetoptError:
        #Modificar para coincidir con tarea
        print("Use: python OUILookup.py --ip <IP> | --Arg2 <Arg2> | --Arg3 | [--help] \n --ip : IP del host a consultar. \n --Arg2:  \n --Atg3: \n --help:")
        sys.exit(2)
        
    for opt, arg in opts:
        if opt in ("-i", "--ip"):
            if pertenece_a_red(arg):
                print(MISMA_RED.format(mac=obtener_mac_por_ip(arg), manufacturer=obtener_datos_por_ip(arg) if obtener_datos_por_ip(arg) != "" else "Not found"))
            else:
                print(OTRA_RED)
        elif opt in ("--mac"):
            vendor, time = obtener_fabricante_mac(arg).values()
            print(MAC_EN_BASE_DE_DATOS.format(mac=arg, manufacturer=vendor + f"\nTiempo de respuesta: {time}ms"))
        elif opt in ("--arp"):
            print(obtener_tabla_arp())
        elif opt in ("--help"):
            print(AYUDA)
        else:
            print("Debe proporcionar una opción válida (-i, -m o -a).")
            sys.exit(2)
        sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])