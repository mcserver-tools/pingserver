import os
import socketserver
import json
from datetime import datetime, timedelta
from socketserver import TCPServer
from threading import Lock, Thread
from time import sleep

from database import db_manager

os.system('color')

server_inst = None

class Server():
    def __init__(self) -> None:
        self.active_addresses = []
        self._lock = Lock()

        self.add_to_db = []


        global server_inst
        server_inst = self

    def start(self):
        self._start_socketserver()
        self._write_to_db()

    def _write_to_db(self):
        while True:
            if len(self.add_to_db) > 0:
                for c in range(len(self.add_to_db)):
                    db_manager.INSTANCE.add_address(self.add_to_db.pop(0))

            c = 0
            while c < len(self.active_addresses):
                if (datetime.now() - self.active_addresses[c][1]) > timedelta(days=0, hours=0, minutes=1, seconds=0, milliseconds=0):
                    print(f"{bcolors.WARNING}Timeout for client {self.active_addresses[c][0]}!{bcolors.ENDC}")
                    with self._lock:
                        with open("pingserver/address_cache.txt", "a") as f:
                            f.write("\n" + self.active_addresses.pop(c)[0])
                    c -= 1
                c += 1
            sleep(1)

    def _start_socketserver(self):
        server = TCPServer(("192.168.0.154", 20005), TCPSocketHandler)
        print("Starting server...")
        Thread(target=server.serve_forever, daemon=True).start()

    def keepalive(self, address):
        for c, item in enumerate(self.active_addresses):
            if item[0] == address:
                self.active_addresses[c] = (item[0], datetime.now())
                return True
        return False

    def _get_address(self):
        with self._lock:
            with open("pingserver/address_cache.txt", "r+") as f:
                lines = f.readlines()

        if len(lines) == 1 and len(lines[0].split(".")) == 4:
            last_address = lines[0]
            lines = [self._increase_address(lines[0])]
        elif len(lines) > 1 and len(lines[-1].split(".")) == 4:
            print(lines)
            last_address = lines.pop()
            lines[-1] = lines[-1].split("\n")[0]
            print(lines)
        else:
            last_address = "1.1.0.0"
            lines = [self._increase_address("1.1.0.0")]

        self.active_addresses.append((last_address, datetime.now()))

        with self._lock:
            with open("pingserver/address_cache.txt", "w+") as f:
                f.writelines(lines)

        return last_address

    def _increase_address(self, last_address):
        addr = last_address.split(".")
        if int(addr[1]) + 1 > 255:
            last_address = f"{int(addr[0]) + 1}.1.0.0"
        else:
            last_address = f"{addr[0]}.{int(addr[1]) + 1}.0.0"
        return last_address

class TCPSocketHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        global server_inst

        text = ReceiveText(self)
        if text.startswith("KEEPALIVE"):
            address = text.split(" ", maxsplit=1)[1]
            if server_inst.keepalive(address):
                SendText(self, "200 OK")
                return
            else:
                self.errored(text, error_msg="404 UNKNOWN ADDRESS")
                return
        elif text.startswith("PING"):
            SendText(self, "200 OK")
        elif text.startswith("POST"):
            print(text.rsplit(" [", maxsplit=1)[0] + " [...]", end="\r")
            if not self._receive_addresses(text):
                self.errored(text)
                return
        else:
            print(text, end="\r")

            if text.startswith("GET"):
                split_text = text.split(" ", maxsplit=1)[1]
                if split_text.startswith("address"):
                    address = server_inst._get_address()
                    SendText(self, address)
                else:
                    self.errored(text)
                    return
            else:
                self.errored(text)
                return

        if not text.startswith("POST"):
            print(f"> {bcolors.OKGREEN}{text}{bcolors.ENDC}")
        else:
            print(f"> {bcolors.OKGREEN}{text.rsplit(' [', maxsplit=1)[0]} [...]{bcolors.ENDC}")
        print("Request handled successfully.")

    def errored(self, text, error_msg = "404 Unknown REQUEST"):
        if not text.startswith("POST"):
            print(f"> {bcolors.FAIL}{text}{bcolors.ENDC}")
        else:
            print(f"> {bcolors.FAIL}{text.rsplit(' [', maxsplit=1)[0]} [...]{bcolors.ENDC}")
        print(error_msg)
        SendText(self, error_msg)

    def _receive_addresses(self, text):
        split_text = text.split(" ", maxsplit=1)[1]
        if split_text.startswith("address"):
            split_text = split_text.split(" ", maxsplit=1)[1]
            client_address, addresses = split_text.split(" ", maxsplit=1)

            found = False
            for c, item in enumerate(server_inst.active_addresses):
                if item[0] == client_address:
                    server_inst.active_addresses.pop(c)
                    found = True
            if not found:
                self.errored(text, error_msg="404 UNKNOWN ADDRESS")
                return
            try:
                addresses = addresses.replace("'", '"')
                address_list = json.loads(addresses)
            except:
                self.errored(text, error_msg="404 LIST CONVERTION FAILED")
                return

            server_inst.add_to_db += address_list

            SendText(self, "200 OK")
            return True
        else:
            return False

def SendText(self, text: str):
    self.request.sendall(StringToBytes(text))

def ReceiveText(self) -> str:
    return BytesToString(self.request.recv(4096))

def StringToBytes(input):
    return bytes(input, 'utf-8')

def BytesToString(bytes):
    return bytes.decode()

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
