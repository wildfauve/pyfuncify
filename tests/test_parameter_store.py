import pytest

import os

from pyfuncify import parameter_store, aws_client_helpers

from .shared import aws_helpers, ssm_helpers


def test_initialises_env_from_ps(setup_aws_ctx):
    parameter_store.set_env_from_parameter_store(path='/test/test_function/function_namespace/environment/')
    
    assert os.environ.get('CLIENT_ID') == "id"
    assert os.environ.get('CLIENT_SECRET') == "secret"
    assert os.environ.get('IDENTITY_TOKEN_ENDPOINT') == "https://test.host/token"



@pytest.fixture
def setup_aws_ctx():
    services = {'ssm': {}}

    aws_client_helpers.invalidate_cache()

    aws_helpers.MockSsm.response = ssm_helpers.ssm_param_response()

    aws_helpers.MockSsm().get_parameters_by_path("", True)

    aws_client_helpers.AwsClientConfig().configure(region_name="ap_southeast_2",
                                                   aws_client_lib=aws_helpers.MockBoto3(mock_client=aws_helpers.MockSsm),
                                                   services=services)
