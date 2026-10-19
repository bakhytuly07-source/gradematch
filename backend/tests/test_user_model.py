import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.schemas import User as PublicUser


def test_normalized_user_roundtrip(database):
    with database() as db:
        user = User(email=' USER@Example.com ', password_hash='$2b$hash')
        db.add(user)
        db.commit()
        id, timestamp = user.id, user.created_at
    with database() as db:
        user = db.get(User, id)
        assert user.email == 'user@example.com'
        assert user.password_hash == '$2b$hash'
        assert user.created_at == timestamp
        assert PublicUser.model_validate(user).model_dump() == {'id': id, 'email': user.email}
        db.add(User(email='User@example.com', password_hash='other'))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.get(User, id).password_hash == '$2b$hash'


@pytest.mark.parametrize('values', [{'password_hash': 'hash'}, {'email': 'a@b.co'}])
def test_user_required_fields(database, values):
    with database() as db:
        db.add(User(**values))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()
