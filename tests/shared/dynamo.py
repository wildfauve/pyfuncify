import pytest
from moto import mock_dynamodb2

@pytest.fixture
def dynamo_mock_empty():

    mock_dynamodb2().start()

    from . base_model import BaseModel

    if not BaseModel.exists():
        BaseModel.create_table()

    yield BaseModel

    mock_dynamodb2().stop()
