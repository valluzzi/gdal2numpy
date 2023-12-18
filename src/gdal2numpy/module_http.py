import socket
import requests
from .module_log import Logger

def hostname():
    """
    hostname
    """
    return socket.gethostname()


def local_ip():
    """
    get_ip -
    https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0)
    try:
        # doesn't even have to be reachable
        s.connect(("10.254.254.254", 1))
        res = s.getsockname()[0]
    except socket.error:
        res = "127.0.0.1"
    finally:
        s.close()
    return res


def whatsmyip():
    """
    whatsmyip
    """
    uris = ["https://checkip.amazonaws.com",
            "https://ifconfig.co/ip", 
            "https://ipinfo.io/ip", 
            "https://icanhazip.com",
            "https://api.ip.sb/ip", 
            "https://api.ipify.org"]
    for uri in uris:
        try:
            return requests.get(uri).text.strip()
        except requests.exceptions.RequestException:
            continue
    return None


def http_get(url, mode=""):
    """
    http_get use requests
    """
    if url and isinstance(url, str) and url.startswith("http"):
        try:
            print(url)
            with requests.get(url) as response:
                if response.status_code == 200:
                    if mode == "json":
                        return response.json()
                    elif mode == "text":
                        return response.text
                    return response.content
        except requests.exceptions.RequestException as ex:
            Logger.error(ex)
    return None




