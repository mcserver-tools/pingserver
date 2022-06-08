"""Module containing the Server class"""

import os
import socketserver
import json
from pathlib import Path
from datetime import datetime, timedelta
from socketserver import TCPServer
from threading import Lock, Thread
from time import sleep

from db_manager import DBManager
from bcolors import BColors

if os.name == "nt":
    os.system('color')

class Server():
    """Class containing all methods concerning the pingserver"""

    def __init__(self, address="192.168.0.154") -> None:
        if not Server.INSTANCE:
            self._address = (address, 20005)

            # timedelta after which an address is considered timed out
            self._timeout = timedelta(days=0,hours=0, minutes=1, seconds=0, milliseconds=0)

            self.active_addresses: list[tuple[str, datetime]] = []
            self._lock = Lock()

            self.add_to_db = []

            Server.INSTANCE = self

    INSTANCE = None

    def start(self):
        """Start the server"""

        self._start_socketserver()
        self._write_to_db()

    def get_address(self):
        """Get the next address from the cache file"""

        # create the cache file if it doesn't exist
        with self._lock:
            if not Path("address_cache.txt").is_file():
                with open("address_cache.txt", "w", encoding="utf8") as file:
                    file.write("1.1.0.0")

        with self._lock:
            with open("address_cache.txt", "r+", encoding="utf8") as file:
                lines = file.readlines()

        # if only one address is in the file, take it and increment the saved address
        if len(lines) == 1 and len(lines[0].split(".")) == 4:
            last_address = lines[0]
            lines = [self._increase_address(lines[0])]
        # if more than one address is in the file, pop the last address
        elif len(lines) > 1 and len(lines[-1].split(".")) == 4:
            last_address = lines.pop()
            lines[-1] = lines[-1].split("\n")[0]
        # if the cache file is corrupted, use the first address
        else:
            last_address = "1.1.0.0"
            lines = [self._increase_address("1.1.0.0")]

        self.active_addresses.append((last_address, datetime.now()))

        # save the new address list
        with self._lock:
            with open("address_cache.txt", "w+", encoding="utf8") as file:
                file.writelines(lines)

        return last_address

    def keepalive(self, address):
        """Refreshes the keepalive timer"""

        for index, item in enumerate(self.active_addresses):
            if item[0] == address:
                self.active_addresses[index] = (item[0], datetime.now())
                return True
        return False

    def _start_socketserver(self):
        """Start the socketserver"""

        server = TCPServer(self._address, TCPSocketHandler)
        print("Starting server...")
        Thread(target=server.serve_forever, daemon=True).start()

    def _write_to_db(self):
        """Add working addresses to database"""

        while True:
            if len(self.add_to_db) > 0:
                for _ in range(len(self.add_to_db)):
                    DBManager().add_address(self.add_to_db.pop())
            self._check_timeouts()

    def _check_timeouts(self):
        """Checks if an address has timed out"""

        counter = 0
        while counter < len(self.active_addresses):
            if (datetime.now() - self.active_addresses[counter][1]) > self._timeout:
                print(f"{BColors.WARNING}Timeout for client " +
                        f"{self.active_addresses[counter][0]}!{BColors.ENDC}")
                with self._lock:
                    with open("address_cache.txt", "a", encoding="utf8") as file:
                        file.write("\n" + self.active_addresses.pop(counter)[0])
                counter -= 1
            counter += 1
        sleep(1)

    @staticmethod
    def _increase_address(last_address):
        """Increase and return the given address"""

        addr = last_address.split(".")
        if int(addr[1]) + 1 > 255:
            if int(addr[0]) + 1 > 255:
                last_address = "1.1.0.0"
            else:
                last_address = f"{int(addr[0]) + 1}.1.0.0"
        else:
            last_address = f"{addr[0]}.{int(addr[1]) + 1}.0.0"
        return last_address

class TCPSocketHandler(socketserver.BaseRequestHandler):
    """Class handling incoming Tcp requests"""

    def handle(self) -> None:
        """Handle a request"""

        text = self.receive_text()

        # send back OK
        if text.startswith("PING"):
            self.send_text("OK")
            return

        # refresh the keepalive timer
        if text.startswith("KEEPALIVE"):
            address = text.split(" ", maxsplit=1)[1]
            if Server.INSTANCE.keepalive(address):
                self.send_text("OK")
                return
            self.errored(text, error_msg="ERROR:UNKNOWN ADDRESS")
            return

        # save the received working addresses to the database
        if text.startswith("PUT"):
            print(text.rsplit(" [", maxsplit=1)[0] + " [...]", end="\r")
            if not self._receive_addresses(text):
                self.errored(text, error_msg="ERROR:LIST CONVERTION FAILED")
                return
        # send back a new address
        elif text.startswith("GET"):
            print(text, end="\r")
            split_text = text.split(" ", maxsplit=1)[1]
            if split_text.startswith("address"):
                address = Server.INSTANCE.get_address()
                self.send_text(address)
            else:
                self.errored(text)
                return
        # handle unknown requests
        else:
            self.errored(text)
            return

        # replace the sent addresses with [...]
        if text.startswith("PUT"):
            text = f"{text.rsplit(' [', maxsplit=1)[0]} [...]"

        print(f"> {BColors.OKGREEN}{text}{BColors.ENDC}")
        print("Request handled successfully.")

    def errored(self, text, error_msg = "ERROR:Unknown REQUEST"):
        """Handle errored requests"""

        # replace the sent addresses with [...]
        if text.startswith("PUT"):
            text = f"{text.rsplit(' [', maxsplit=1)[0]} [...]"

        print(f"> {BColors.FAIL}{text}{BColors.ENDC}")

        print(error_msg)
        self.send_text(error_msg)

    def _receive_addresses(self, text):
        """Handle received working addresses"""

        split_text = text.split(" ", maxsplit=1)[1]
        # return if the put request is unknown
        if not split_text.startswith("address"):
            return False

        split_text = split_text.split(" ", maxsplit=1)[1]
        client_address, addresses = split_text.split(" ", maxsplit=1)

        found = False
        for index, item in enumerate(Server.INSTANCE.active_addresses):
            if item[0] == client_address:
                popped_item = Server.INSTANCE.active_addresses.pop(index)
                found = True
        # return if the client address wasn't found
        if not found:
            return False

        # try parsing the string to a list
        try:
            addresses = addresses.replace("'", '"')
            address_list = json.loads(addresses)
        # return if the parsing failed
        except json.decoder.JSONDecodeError:
            Server.INSTANCE.active_addresses.append(popped_item)
            return False

        Server.INSTANCE.add_to_db += address_list
        self.send_text("200 OK")
        return True

    def send_text(self, text: str):
        """Send string to the given socket"""

        self.request.sendall(self._string_to_bytes(text))

    def receive_text(self) -> str:
        """Receive string from the given socket"""

        return self._bytes_to_string(self.request.recv(65536))

    @staticmethod
    def _string_to_bytes(input_text):
        """Convert string to bytes object"""

        return bytes(input_text, 'utf-8')

    @staticmethod
    def _bytes_to_string(input_bytes):
        """Convert bytes object to string"""

        return input_bytes.decode()
