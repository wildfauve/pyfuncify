from pyfuncify import app_web_session

def it_created_a_session_from_a_multi_property_cookie():
    session = app_web_session.WebSession().session_from_headers({'Cookie': "session1=1; session2=2"})

    assert len(session.properties) == 2

    props = [(prop.name, prop.serialise()) for prop in session.properties]

    assert props == [('session1', 'session1=1'), ('session2', 'session2=2')]


def it_serialises_session_as_multi_hdr_set_cookie():
    session = app_web_session.WebSession().session_from_headers({'Cookie': "session1=1; session2=2"})

    assert session.serialise_state_as_multi_header() == {'Set-Cookie': ['session1=1', 'session2=2']}


def it_gets_a_property():
    session = app_web_session.WebSession().session_from_headers({'Cookie': "session1=1; session2=2"})

    assert session.get('session1').value() == '1'

def it_doesnt_serialise_when_no_props():
    session = app_web_session.WebSession().session_from_headers(None)

    assert session.serialise_state_as_multi_header() == {}

def it_sets_new_property():
    session = app_web_session.WebSession().session_from_headers(None)

    session.set('session1', '1')

    assert session.get('session1').value() == '1'


def it_updates_a_property():
    session = app_web_session.WebSession().session_from_headers({'Cookie': "session1=1"})

    session.set('session1', '2')

    assert session.get('session1').value() == '2'
