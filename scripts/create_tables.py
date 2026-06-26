from app.db.session import Base, engine
from app.models import tables  # noqa
Base.metadata.create_all(bind=engine)
print('OK: tables created')
