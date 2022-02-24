from pingserver.server import Server
from database.db_manager import DBManager

if __name__ == "__main__":
    DBManager()
    Server().start()
