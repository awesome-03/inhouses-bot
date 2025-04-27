from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


engine = create_engine('sqlite:///database/database.db', echo=True)
session = sessionmaker(bind=engine)
