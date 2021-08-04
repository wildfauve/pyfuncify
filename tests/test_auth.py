import pytest

from slack_sdk.signature import SignatureVerifier

def test_generate_signature(valid_signature):
    verifier = SignatureVerifier(valid_signature['signing_secret'])
    signature = verifier.generate_signature(
        timestamp=valid_signature['x_slack_request_timestamp'], body=valid_signature['body']
    )
    assert valid_signature['x_slack_sig'] == signature

@pytest.fixture
def valid_signature() -> dict:
    return {
        'body': "{\"token\":\"vEjfyyNOymjEk2qpJGTQe05b\",\"team_id\":\"T09U5C4JH\",\"api_app_id\":\"A027D9QM2Q7\",\"event\":{\"client_msg_id\":\"1446e6fd-d010-463a-9027-56efe3c11e51\",\"type\":\"app_mention\",\"text\":\"<@U027MCA26G6> fp spk\",\"user\":\"U09U563QC\",\"ts\":\"1627449785.000300\",\"team\":\"T09U5C4JH\",\"blocks\":[{\"type\":\"rich_text\",\"block_id\":\"dk3y\",\"elements\":[{\"type\":\"rich_text_section\",\"elements\":[{\"type\":\"user\",\"user_id\":\"U027MCA26G6\"},{\"type\":\"text\",\"text\":\" fp spk\"}]}]}],\"channel\":\"C264UFQSX\",\"event_ts\":\"1627449785.000300\"},\"type\":\"event_callback\",\"event_id\":\"Ev029DV9CYCB\",\"event_time\":1627449785,\"authorizations\":[{\"enterprise_id\":null,\"team_id\":\"T09U5C4JH\",\"user_id\":\"U027MCA26G6\",\"is_bot\":true,\"is_enterprise_install\":false}],\"is_ext_shared_channel\":false,\"event_context\":\"3-app_mention-T09U5C4JH-A027D9QM2Q7-C264UFQSX\"}",
        'x_slack_sig': "v0=911a5a9624a9802adf2ded7ad49c938ea055d6b2b536faa8c9af1265881744d0",
        'signing_secret': "926496778547a66a753a6ecee5123a92",
        'x_slack_request_timestamp': 1627449786}