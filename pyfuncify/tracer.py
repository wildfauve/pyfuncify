import uuid

class Tracer():

    def __init__(self, env):
        self.env = env
        self.handler_id = uuid.uuid4()

    def serialise(self):
        return {'env': self.env, 'handler_id': self.handler_id_to_s()}

    def handler_id_to_s(self):
        return str(self.handler_id) if isinstance(self.handler_id, uuid.UUID) else self.handler_id


def init_tracing(env):
    return Tracer(env)
