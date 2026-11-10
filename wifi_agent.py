"""Read real RSSI from the connected Windows Wi-Fi adapter and post it to the app."""

import ctypes
from ctypes import wintypes
import json
import os
import time
from urllib.request import Request, urlopen


APP_URL = "http://127.0.0.1:5000/api/readings"
WLAN_INTF_OPCODE_RSSI = 0x10000102
WLAN_INTERFACE_STATE_CONNECTED = 1


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class WLAN_INTERFACE_INFO(ctypes.Structure):
    _fields_ = [
        ("InterfaceGuid", GUID),
        ("description", wintypes.WCHAR * 256),
        ("state", wintypes.DWORD),
    ]


class WLAN_INTERFACE_INFO_LIST(ctypes.Structure):
    _fields_ = [
        ("number_of_items", wintypes.DWORD),
        ("index", wintypes.DWORD),
        ("interfaces", WLAN_INTERFACE_INFO * 1),
    ]


def read_connected_wifi_rssi():
    if os.name != "nt":
        raise RuntimeError("The sensor agent must run directly on Windows, outside Docker.")

    wlan = ctypes.WinDLL("wlanapi.dll")
    wlan.WlanOpenHandle.argtypes = [wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.HANDLE)]
    wlan.WlanOpenHandle.restype = wintypes.DWORD
    wlan.WlanEnumInterfaces.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(WLAN_INTERFACE_INFO_LIST))]
    wlan.WlanEnumInterfaces.restype = wintypes.DWORD
    wlan.WlanQueryInterface.argtypes = [wintypes.HANDLE, ctypes.POINTER(GUID), wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    wlan.WlanQueryInterface.restype = wintypes.DWORD
    wlan.WlanFreeMemory.argtypes = [ctypes.c_void_p]
    wlan.WlanFreeMemory.restype = None
    wlan.WlanCloseHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    wlan.WlanCloseHandle.restype = wintypes.DWORD
    handle = wintypes.HANDLE()
    negotiated_version = wintypes.DWORD()
    result = wlan.WlanOpenHandle(2, None, ctypes.byref(negotiated_version), ctypes.byref(handle))
    if result != 0:
        raise OSError(result, "Windows could not open the WLAN API")

    interface_list = ctypes.POINTER(WLAN_INTERFACE_INFO_LIST)()
    try:
        result = wlan.WlanEnumInterfaces(handle, None, ctypes.byref(interface_list))
        if result != 0:
            raise OSError(result, "Windows could not enumerate Wi-Fi adapters")

        base = ctypes.addressof(interface_list.contents)
        first = WLAN_INTERFACE_INFO_LIST.interfaces.offset
        item_size = ctypes.sizeof(WLAN_INTERFACE_INFO)
        for index in range(interface_list.contents.number_of_items):
            address = base + first + index * item_size
            interface = ctypes.cast(address, ctypes.POINTER(WLAN_INTERFACE_INFO)).contents
            if interface.state != WLAN_INTERFACE_STATE_CONNECTED:
                continue

            data_size = wintypes.DWORD()
            data = ctypes.c_void_p()
            result = wlan.WlanQueryInterface(
                handle,
                ctypes.byref(interface.InterfaceGuid),
                WLAN_INTF_OPCODE_RSSI,
                None,
                ctypes.byref(data_size),
                ctypes.byref(data),
                None,
            )
            if result != 0:
                raise OSError(result, "Windows could not read RSSI from the connected Wi-Fi adapter")
            try:
                rssi = ctypes.cast(data, ctypes.POINTER(ctypes.c_long)).contents.value
            finally:
                wlan.WlanFreeMemory(data)

            if not -100 <= rssi <= 0:
                raise RuntimeError(f"The Wi-Fi driver returned an unexpected RSSI value: {rssi}")
            return rssi, interface.description

        raise RuntimeError("No connected Wi-Fi adapter was found. Connect this laptop to Wi-Fi first.")
    finally:
        if interface_list:
            wlan.WlanFreeMemory(interface_list)
        wlan.WlanCloseHandle(handle, None)


def main():
    if os.name != "nt":
        raise SystemExit("Run this sensor agent in Windows PowerShell, not inside Docker.")
    location = input("Enter this measurement location (for example, Bedroom): ").strip()
    if not location:
        raise SystemExit("A location label is required.")

    print("Reading the connected Wi-Fi adapter every 5 seconds. Press Ctrl+C to stop.")
    while True:
        try:
            rssi, adapter = read_connected_wifi_rssi()
            body = json.dumps({"location": location, "rssi": rssi, "source": "Windows Wi-Fi adapter"}).encode("utf-8")
            req = Request(APP_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(req, timeout=5) as response:
                response.read()
            print(f"{location}: {rssi} dBm via {adapter} — sent to Wi-Fi Signal Survey")
        except Exception as error:
            print(f"Sensor error: {error}")
        time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWi-Fi sensor stopped.")
