"""Main module of the pingserver"""

from database.db_manager import DBManager

from pingserver import server

if __name__ == "__main__":
    DBManager()
    server.INSTANCE.start()
