"""Module for managing the database"""

import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker

from model import Address, Base

INSTANCE = None

class DBManager():
    """Class that manages the database"""

    def __init__(self):
        if INSTANCE is None:
            db_connection = sqlalchemy.create_engine("sqlite:///pingserver/addresses.db",
                                                     connect_args={'check_same_thread': False})
            Base.metadata.create_all(db_connection)

            session_factory = sessionmaker(db_connection, autoflush=False)
            _session = scoped_session(session_factory)
            self.session = _session()

    def add_address(self, address):
        """Add address to database"""

        new_address = Address(address=address)
        self.session.add(new_address)
        try:
            self.session.commit()
        except sqlalchemy.exc.IntegrityError:
            self.session.rollback()

    def get_number_of_addresses(self):
        """Returns number of addresses in database"""

        return self.session.query(Address).count()

    def get_address(self, index):
        """Returns address with given primary key"""

        return self.session.query(Address).get(index).address

    def get_addresses(self):
        """Returns all addresses in database"""

        return [item.address for item in self.session.query(Address).all()]

INSTANCE = DBManager()
