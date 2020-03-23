import asyncio
import logging
import signal
import sys

from mqtt_cmd.config import read_config
from mqtt_cmd.mqtt import MQTTConnectionHandler


def main(args=tuple(sys.argv)):
    stop = asyncio.Event()

    def ask_stop(*a):
        stop.set()

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, ask_stop)
    loop.add_signal_handler(signal.SIGTERM, ask_stop)

    if len(args) < 2:
        raise SystemExit(f"Usage: {sys.argv[0]} [config]")

    cfg_path = args[1]
    cfg = read_config(cfg_path)

    log_level = getattr(logging, cfg.get("log_level", "INFO").upper(), logging.INFO)
    logging.basicConfig(level=log_level)

    handler = MQTTConnectionHandler(cfg)
    loop.run_until_complete(handler.run(stop))
