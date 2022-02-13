import pytest

@pytest.fixture
def s3_event_hello():
    return {
        'Records': [
            {'s3': {'bucket': {'name': 'hello'}, 'object': {'key': 'hello_file.json'}}}
        ]
    }
