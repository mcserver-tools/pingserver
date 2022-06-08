import os
import subprocess
from datetime import datetime, timedelta
from socket import create_connection
from time import sleep

def partial_test():
    from server import Server

    # test the static _increase_address function
    assert Server._increase_address("23.42.0.0") == "23.43.0.0"
    assert Server._increase_address("74.255.0.0") == "75.1.0.0"
    assert Server._increase_address("0.0.0.0") == "0.1.0.0"
    assert Server._increase_address("255.255.0.0") == "1.1.0.0"

def full_test():
    address = ("127.0.0.1", 20005)

    # backup address_cache.txt if it exists
    if os.path.isfile("address_cache.txt") and not os.path.isfile("address_cache.txt.backup"):
        os.rename("address_cache.txt", "address_cache.txt.backup")

    # start the pingserver
    subprocess.Popen(["py", "main.py", "-a", ""])

    # wait for it to start
    sleep(3)

    # try a PING request
    sock = create_connection(address, timeout=5.0)
    _send(sock, "PING")
    assert _recv(sock) == "OK"

    # try GET address requests
    sock = create_connection(address)
    _send(sock, "GET address")
    assert _recv(sock) == "1.1.0.0"

    sock = create_connection(address)
    _send(sock, "GET address")
    assert _recv(sock) == "1.2.0.0"

    sock = create_connection(address)
    _send(sock, "GET address")
    assert _recv(sock) == "1.3.0.0"

    # timing out the first address
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(minutes=2):
        for addr in ["1.2.0.0", "1.3.0.0"]:
            # try sending a keepalive for the other addresses
            sock = create_connection(address)
            _send(sock, f"KEEPALIVE {addr}")
            assert _recv(sock) == "OK"
        sleep(5)

    # the first address should have timed out
    sock = create_connection(address)
    _send(sock, "GET address")
    assert _recv(sock) == "1.1.0.0"

    # the outher addresse should still be active, so we will get a new address
    sock = create_connection(address)
    _send(sock, "GET address")
    assert _recv(sock) == "1.4.0.0"

    os.remove("address_cache.txt")

    # restore the backed up address_cache.txt
    if os.path.isfile("address_cache.txt.backup"):
        os.rename("address_cache.txt.backup", "address_cache.txt")

def _send(sock, text):
    """Send string to the given socket"""

    sock.send(_string_to_bytes(text))

def _recv(sock):
    """Receive string from the given socket"""

    return _bytes_to_string(sock.recv(4096))

@staticmethod
def _string_to_bytes(input_text):
    """Convert string to bytes object"""

    return bytes(input_text, 'utf-8')

@staticmethod
def _bytes_to_string(input_bytes):
    """Convert bytes object to string"""

    return input_bytes.decode()

if __name__ == "__main__":
    partial_test()
    full_test()
