"""Main module of the pingserver"""

import sys

import server

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "-a":
            server.Server(sys.argv[2]).start()
    server.Server().start()
