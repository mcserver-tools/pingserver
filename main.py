"""Main module of the pingserver"""

from db_manager import DBManager

import server

if __name__ == "__main__":
    server.INSTANCE.start()
