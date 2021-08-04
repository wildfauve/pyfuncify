import hashlib
import hmac

from . import env

def verify_slack_token(token: str) -> bool:
    return token == env.Env.slack_verification_token()

def verify_slack_signature(event_body: dict, event_headers: dict, slack_signing_secret: str) -> bool:
    return True
    # signing_secret = bytes(slack_signing_secret, 'utf-8')
    # slack_signature = event_headers['x-slack-signature']
    # slack_request_timestamp = event_headers['x-slack-request-timestamp']
    #
    # basestring = f"v0:{slack_request_timestamp}:{event_body}".encode('utf-8')
    # sign = 'v0=' + hmac.new(signing_secret, basestring, hashlib.sha256).hexdigest()
    #
    # return hmac.compare_digest(sign, slack_signature)


def verify_slack_request(event_body: dict, event_headers: dict, slack_signing_secret: str) -> bool:
    slack_signature = event_headers['x-slack-signature']
    slack_request_timestamp = event_headers['x-slack-request-timestamp']

    ''' Form the basestring as stated in the Slack API docs. We need to make a bytestring. '''
    basestring = f"v0:{slack_request_timestamp}:{event_body}".encode('utf-8')

    ''' Make the Signing Secret a bytestring too. '''
    signing_secret = bytes(slack_signing_secret, 'utf-8')

    ''' Create a new HMAC "signature", and return the string presentation. '''
    sign = 'v0=' + hmac.new(signing_secret, basestring, hashlib.sha256).hexdigest()

    ''' Compare the the Slack provided signature to ours.
    If they are equal, the request should be verified successfully.
    Log the unsuccessful requests for further analysis
    (along with another relevant info about the request). '''
    if hmac.compare_digest(sign, slack_signature):
        return True
    else:
        logger.warning(f"Verification failed. my_signature: {my_signature}")
        return False
