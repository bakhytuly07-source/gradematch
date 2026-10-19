from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.orm import Session
from app.database import make_engine
from app.models import User, Look
from test_api import SETTINGS


def test_migration_upgrade_downgrade_and_rebuild(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'disposable.db'}"
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    engine = make_engine()
    def roundtrip():
        with Session(engine) as db:
            user = User(email='a@b.co', password_hash='hash')
            db.add(user)
            db.flush()
            look = Look(user_id=user.id, name='Migration', style_params=SETTINGS['styleParams'],
                        adjustments=SETTINGS['adjustments'], thumbnail_url='', created_at=1, updated_at=1)
            db.add(look)
            db.commit()
            id = look.id
        with Session(engine) as db:
            assert db.get(Look, id).name == 'Migration'
    command.upgrade(config, 'head')
    command.upgrade(config, 'head')
    roundtrip()
    schema = inspect(engine)
    assert schema.get_unique_constraints('users')[0]['column_names'] == ['email']
    assert schema.get_foreign_keys('looks')[0]['referred_table'] == 'users'
    command.downgrade(config, 'base')
    assert not {'users', 'looks', 'access_tokens'} & set(inspect(engine).get_table_names())
    command.upgrade(config, 'head')
    roundtrip()
    engine.dispose()
