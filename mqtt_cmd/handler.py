import asyncio
import json
import logging
import sys
from functools import partial
from typing import Optional

import aiohttp
import gmqtt as mqtt
import jinja2
import pyjq
from jinja2 import Template


class TopicHandler:
    # noinspection PyProtectedMember
    def __init__(self, topic_cfg: dict):
        self.topic_cfg = topic_cfg
        self.load_json = topic_cfg.get('load_json', False)
        self.jq: Optional[pyjq._pyjq.Script] = None
        self.jinja: Optional[jinja2.Template] = None

        if "jq_query" in topic_cfg:
            if not topic_cfg.get('load_json', True):
                raise ValueError("load_json can't be False when using jq")
            self.jq = pyjq.compile(topic_cfg["jq_query"])
            self.load_json = True

        if "jinja_query" in topic_cfg:
            self.jinja = jinja2.Template(topic_cfg['jinja_query'])

        if self.jinja and self.jq:
            raise ValueError("jinja_query and jq_query can't be both specified at the same time")

    async def handle(self, client: mqtt.Client, topic: str, payload: bytes, qos: int, properties):
        payload = payload.decode(errors="replace")
        value = None
        if self.load_json:
            value = json.loads(payload)

        to_match = payload
        if self.jq:
            to_match = self.jq.first(value)
        elif self.jinja:
            to_match = self.jinja.render(mqtt=client, topic=topic, payload=payload, qos=qos, properties=properties,
                                         value=value)

        for pattern, handlers in self.topic_cfg.get("patterns", []).items():
            if pattern != to_match:
                continue
            for handler_cfg in handlers:
                handler_name, cfg = next(iter(handler_cfg.items()))

                # noinspection PyBroadException
                try:
                    handler = globals().get(f'handle_{handler_name}', None)
                    if not handler:
                        raise ValueError(f'Handler "{handler_name}" does not exist')

                    await handler(cfg, mqtt=client, topic=topic, payload=payload, qos=qos, properties=properties,
                                  value=value)
                except Exception:
                    logging.warning(f"Error executing handler '{handler_name}':", exc_info=sys.exc_info())


async def handle_request(handler_cfg: dict, *a, **kw):
    method = handler_cfg.get('method', 'GET')
    url = handler_cfg['url']
    data = handler_cfg.get('post_data', None)
    headers = handler_cfg.get('headers', None)
    timeout = aiohttp.ClientTimeout(total=handler_cfg.get('timeout', 60))

    if data:
        data = Template(data).render(**kw)

    if headers:
        for k, v in headers.items():
            headers[k] = Template(v).render(**kw)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        await session.request(method, Template(url).render(**kw), data=data, headers=headers)


async def handle_command(handler_cfg: dict, *a, **kw):
    shell = handler_cfg.get('shell', False)
    args = handler_cfg['args']
    stdin = handler_cfg.get('stdin', None)
    timeout = handler_cfg.get('timeout', 5.0)

    if shell and type(args) != str:
        raise ValueError("args must be str when running with shell")
    elif not shell and type(args) != list:
        raise ValueError("args must be list when not running with shell")

    formatted_args = None
    process_creator = None
    if shell:
        formatted_args = Template(args).render(**kw)
        process_creator = partial(asyncio.create_subprocess_shell, formatted_args)
    else:
        formatted_args = map(lambda i: Template(i).render(**kw), args)
        process_creator = partial(asyncio.create_subprocess_exec, *formatted_args)

    p = await process_creator(stdin=asyncio.subprocess.PIPE if stdin else None)

    await asyncio.wait_for(p.communicate(stdin), timeout)
