class BaseEscalation:
    def __init__(self, name, status, config, args):
        self.name = name
        self.status = status
        self.config = config
        self.args = args

        assert self.status and self.config, "Must specify status and config"

    def run(self):
        pass
