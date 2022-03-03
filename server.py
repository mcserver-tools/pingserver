"""Module containing the Server class"""

import os
import socketserver
import json
from datetime import datetime, timedelta
from socketserver import TCPServer
from threading import Lock, Thread
from time import sleep

import db_manager
from bcolors import BColors

os.system('color')

INSTANCE = None

class Server():
    """Class containing all methods concerning the pingserver"""

    def __init__(self) -> None:
        if not INSTANCE:
            self.active_addresses = []
            self._lock = Lock()

            self.add_to_db = []

    def start(self):
        """Start the server"""

        self._start_socketserver()
        self._write_to_db()

    def _write_to_db(self):
        """Write working addresses to database"""

        while True:
            if len(self.add_to_db) > 0:
                for _ in range(len(self.add_to_db)):
                    db_manager.INSTANCE.add_address(self.add_to_db.pop(0))

            counter = 0
            while counter < len(self.active_addresses):
                if (datetime.now() - self.active_addresses[counter][1]) > \
                    timedelta(days=0,hours=0, minutes=1, seconds=0, milliseconds=0):
                    print(f"{BColors.WARNING}Timeout for client " +
                          f"{self.active_addresses[counter][0]}!{BColors.ENDC}")
                    with self._lock:
                        with open("pingserver/address_cache.txt", "a", encoding="utf8") as file:
                            file.write("\n" + self.active_addresses.pop(counter)[0])
                    counter -= 1
                counter += 1
            sleep(1)

    @staticmethod
    def _start_socketserver():
        """Start the socketserver"""

        server = TCPServer(("192.168.0.154", 20005), TCPSocketHandler)
        print("Starting server...")
        Thread(target=server.serve_forever, daemon=True).start()

    def keepalive(self, address):
        """Refresh keepalive timer"""

        for index, item in enumerate(self.active_addresses):
            if item[0] == address:
                self.active_addresses[index] = (item[0], datetime.now())
                return True
        return False

    def get_address(self):
        """Get an address from the file"""

        with self._lock:
            with open("pingserver/address_cache.txt", "r+", encoding="utf8") as file:
                lines = file.readlines()

        if len(lines) == 1 and len(lines[0].split(".")) == 4:
            last_address = lines[0]
            lines = [self._increase_address(lines[0])]
        elif len(lines) > 1 and len(lines[-1].split(".")) == 4:
            last_address = lines.pop()
            lines[-1] = lines[-1].split("\n")[0]
        else:
            last_address = "1.1.0.0"
            lines = [self._increase_address("1.1.0.0")]

        self.active_addresses.append((last_address, datetime.now()))

        with self._lock:
            with open("pingserver/address_cache.txt", "w+", encoding="utf8") as file:
                file.writelines(lines)

        return last_address

    @staticmethod
    def _increase_address(last_address):
        """Increase and return the given address"""

        addr = last_address.split(".")
        if int(addr[1]) + 1 > 255:
            last_address = f"{int(addr[0]) + 1}.1.0.0"
        else:
            last_address = f"{addr[0]}.{int(addr[1]) + 1}.0.0"
        return last_address

class TCPSocketHandler(socketserver.BaseRequestHandler):
    """Class handling incoming Tcp requests"""

    def handle(self) -> None:
        """Handle a received request"""

        text = self.receive_text()
        if text.startswith("KEEPALIVE"):
            address = text.split(" ", maxsplit=1)[1]
            if INSTANCE.keepalive(address):
                self.send_text("200 OK")
                return
            self.errored(text, error_msg="404 UNKNOWN ADDRESS")
            return
        if text.startswith("PING"):
            self.send_text("200 OK")
        elif text.startswith("POST"):
            print(text.rsplit(" [", maxsplit=1)[0] + " [...]", end="\r")
            if not self._receive_addresses(text):
                self.errored(text, error_msg="404 LIST CONVERTION FAILED")
                return
        else:
            print(text, end="\r")

            if text.startswith("GET"):
                split_text = text.split(" ", maxsplit=1)[1]
                if split_text.startswith("address"):
                    address = INSTANCE.get_address()
                    self.send_text(address)
                else:
                    self.errored(text)
                    return
            else:
                self.errored(text)
                return

        if not text.startswith("POST"):
            print(f"> {BColors.OKGREEN}{text}{BColors.ENDC}")
        else:
            print(f"> {BColors.OKGREEN}{text.rsplit(' [', maxsplit=1)[0]} [...]{BColors.ENDC}")
        print("Request handled successfully.")

    def errored(self, text, error_msg = "404 Unknown REQUEST"):
        """Method that handles an request handling error"""

        if not text.startswith("POST"):
            print(f"> {BColors.FAIL}{text}{BColors.ENDC}")
        else:
            print(f"> {BColors.FAIL}{text.rsplit(' [', maxsplit=1)[0]} [...]{BColors.ENDC}")
        print(error_msg)
        self.send_text(error_msg)

    def _receive_addresses(self, text):
        """Handle received working addresses"""

        split_text = text.split(" ", maxsplit=1)[1]
        if split_text.startswith("address"):
            split_text = split_text.split(" ", maxsplit=1)[1]
            client_address, addresses = split_text.split(" ", maxsplit=1)

            found = False
            for index, item in enumerate(INSTANCE.active_addresses):
                if item[0] == client_address:
                    popped_item = INSTANCE.active_addresses.pop(index)
                    found = True
            if not found:
                return False
            try:
                addresses = addresses.replace("'", '"')
                address_list = json.loads(addresses)
            except json.decoder.JSONDecodeError:
                INSTANCE.active_addresses.append(popped_item)
                return False

            INSTANCE.add_to_db += address_list

            self.send_text("200 OK")
            return True
        return False

    def send_text(self, text: str):
        """Send string to the given socket"""

        self.request.sendall(self._string_to_bytes(text))

    def receive_text(self) -> str:
        """Receive string from the given socket"""

        return self._bytes_to_string(self.request.recv(4096))

    @staticmethod
    def _string_to_bytes(input_text):
        """Convert string to bytes object"""

        return bytes(input_text, 'utf-8')

    @staticmethod
    def _bytes_to_string(input_bytes):
        """Convert bytes object to string"""

        return input_bytes.decode()

INSTANCE = Server()
