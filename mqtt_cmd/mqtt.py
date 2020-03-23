import asyncio
import logging
from typing import MutableMapping, List, Optional

import gmqtt as mqtt

from mqtt_cmd.handler import TopicHandler


def mqtt_topic_matches(topic, pattern):
    if '+' not in pattern and '#' not in pattern:
        return topic == pattern
    elif pattern.endswith('#'):
        return topic.startswith(pattern[:-1])
    else:
        head, tail = pattern.split('+', 1)
        return topic.startswith(head) \
            and topic.endswith(tail) \
            and '/' not in topic.replace(head, '').replace(tail, '')


class MQTTConnectionHandler:
    def __init__(self, cfg: dict):
        self._cfg = cfg
        self._client: Optional[mqtt.Client] = None
        self._topic_handlers: MutableMapping[str, List[TopicHandler]] = {}

    async def connect(self):
        self._client = mqtt.Client(client_id=self._cfg["mqtt"].get("client_id", "mqtt-cmd"))
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        await self._client.connect(self._cfg["mqtt"]["host"], self._cfg["mqtt"].get("port", 1883), keepalive=60)
        logging.debug(f"Connected to broker {self._cfg['mqtt']['host']}")

    async def run(self, stop: asyncio.Event):
        await self.connect()
        await stop.wait()
        await self._client.disconnect()

    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        for topic in self._cfg["topics"]:
            name, cfg = next(iter(topic.items()))

            if name not in self._topic_handlers:
                self._topic_handlers[name] = []

            self._topic_handlers[name].append(TopicHandler(cfg))
            self._client.subscribe(name)

    async def on_message(self, client: mqtt.Client, topic: str, payload: bytes, qos: int, properties):
        for handler_topic, handlers in self._topic_handlers.items():
            if mqtt_topic_matches(topic, handler_topic):
                for handler in handlers:
                    await handler.handle(client, topic, payload, qos, properties)
