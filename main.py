from pingserver.server import Server
from database import db_manager

if __name__ == "__main__":
    db_manager.instance
    Server().start()
