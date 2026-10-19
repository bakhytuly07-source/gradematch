from alembic import context
from app.database import Base, make_engine
from app import models  # noqa: F401 - register ORM metadata

engine = make_engine()

if context.is_offline_mode():
    context.configure(url=engine.url, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

engine.dispose()
