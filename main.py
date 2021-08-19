from cae import app
from cae.config import config
from cae.operators import launch_operators
from cae.channel.services.sshd import SSHServer
from gunicorn.app.base import BaseApplication
from pretty_logging import pretty_logger
import multiprocessing
import signal


class WebApplication(BaseApplication):

    def __init__(self, application, options=None):
        self.options = options or {}
        self.application = application
        super().__init__()

    def load_config(self):
        the_config = {key: value for key, value in self.options.items()
                      if key in self.cfg.settings and value is not None}
        for key, value in the_config.items():
            self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def start_server():

    def _start_server():
        options = {
            "bind": "{}:{}".format("0.0.0.0", "{}".format(config.get("PORT"))),
            "workers": config.get("WORKERS"),
            "accesslog": "-",
            "errorlog": "-",
        }
        WebApplication(app, options).run()

    process = multiprocessing.Process(target=_start_server, daemon=False)
    process.start()
    return process


def start_operator():
    process = multiprocessing.Process(target=launch_operators, daemon=False)
    process.start()
    return process


def start_channel():

    def _start_channel():
        pretty_logger.info("start cae channel server")
        sshd = SSHServer()
        sshd.run()

    process = multiprocessing.Process(target=_start_channel, daemon=False)
    process.start()
    return process


def main():

    start_server()
    start_operator()
    channel_proc = start_channel()

    def exit_kill(sig, frame):
        channel_proc.kill()
        pretty_logger.info("shutdown bye bye")
    for sig in [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]:
        signal.signal(sig, exit_kill)
    signal.pause()


if __name__ == "__main__":
    main()
