from pretty_logging import pretty_logger
from .traefik import traefik_operator
import threading
import signal


def launch_operators():
    # start traefik operator
    threading.Thread(target=traefik_operator, daemon=True).start()
    pretty_logger.info("start traefik operator")

    def _on_exit(sig, frame):
        pretty_logger.info("operators exit")

    for sig in [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]:
        signal.signal(sig, _on_exit)
    signal.pause()
