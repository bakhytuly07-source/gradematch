import pytest
from app.models import Look, User
from app.schemas import Look as PublicLook
from test_api import SETTINGS


def record(owner, **values):
    return Look(user_id=owner, name='Same', style_params=SETTINGS['styleParams'],
                adjustments=SETTINGS['adjustments'], created_at=1700000000000,
                updated_at=1700000000001, **values)


def test_look_roundtrip_and_owners(database):
    with database() as db:
        users = [User(email=f'{i}@example.com', password_hash='hash') for i in range(2)]
        db.add_all(users)
        db.flush()
        looks = [record(u.id, is_favorite=bool(i)) for i, u in enumerate(users)]
        db.add_all(looks)
        db.commit()
        ids, owners = [l.id for l in looks], [u.id for u in users]
    with database() as db:
        for i, id in enumerate(ids):
            look = db.get(Look, id)
            public = PublicLook.model_validate(look).model_dump(by_alias=True)
            assert look.user_id == owners[i]
            assert public['style_params'] == SETTINGS['styleParams']
            assert public['adjustments'] == SETTINGS['adjustments']
            assert public['is_favorite'] == bool(i)
            assert public['created_at'] == 1700000000000
            assert public['updated_at'] == 1700000000001
            assert public['thumbnail_url'] == '' and 'user_id' not in public
        assert set(Look.__table__.columns.keys()) == {'id', 'user_id', 'name', 'style_params',
            'adjustments', 'thumbnail_url', 'is_favorite', 'created_at', 'updated_at'}


def test_missing_owner_and_original_thumbnail_rejected(database):
    with database() as db:
        db.add(record('missing'))
        with pytest.raises(ValueError, match='owner'):
            db.flush()
        db.rollback()
        user = User(email='a@b.co', password_hash='hash')
        db.add(user)
        db.flush()
        db.add(record(user.id, thumbnail_url='data:image/png;base64,bad'))
        with pytest.raises(Exception):
            db.flush()
        db.rollback()
