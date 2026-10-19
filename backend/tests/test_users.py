from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import pytest

from app.errors import ApiError
from app.passwords import verify_password
from app.users import MemoryUsers


def test_normalized_unique_accounts_and_passwords(caplog):
    repo=MemoryUsers()
    user=repo.create('  A@Example.com  ','password-unique-secret')
    assert user.email=='a@example.com'
    assert user.password_hash.startswith('$2')
    assert verify_password('password-unique-secret',user.password_hash)
    assert not verify_password('wrong',user.password_hash)
    assert repo.authenticate(' A@EXAMPLE.COM ','password-unique-secret')==user
    assert repo.authenticate('unknown@example.com','password-unique-secret') is None
    assert repo.authenticate(user.email,'wrong') is None
    with pytest.raises(ApiError) as error:
        repo.create('A@EXAMPLE.COM','replacement-secret')
    assert error.value.status==409
    assert repo.find('a@example.com')==user
    assert repo.authenticate(user.email,'password-unique-secret')==user
    assert user.public().model_dump()=={'id':user.id,'email':'a@example.com'}
    assert user.password_hash not in repr(user)+user.public().model_dump_json()+caplog.text
    assert 'password-unique-secret' not in repr(user)+repr(repo.__dict__)+caplog.text
    with pytest.raises(FrozenInstanceError):
        user.email='changed@example.com'


def test_repository_instances_are_isolated_and_long_passwords_work():
    first,second=MemoryUsers(),MemoryUsers()
    long='é'*100
    user=first.create('same@example.com',long)
    assert second.get(user.id) is None and second.find(user.email) is None
    assert first.authenticate(user.email,long)==user
    assert first.authenticate(user.email,long+'x') is None
    other=second.create(user.email,'other-password')
    assert other.id!=user.id and first.get(other.id) is None


def test_concurrent_normalized_duplicates_do_not_replace_original():
    repo=MemoryUsers()
    def create(email):
        try:
            return repo.create(email,'same-password')
        except ApiError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(create,[' A@Example.com ','a@example.com']))
    assert sum(item==409 for item in results)==1
    user=next(item for item in results if item!=409)
    assert repo.find('a@example.com')==user
