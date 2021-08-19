from cae.config import config
from cae.models import redis_client
from typing import List
from pretty_logging import pretty_logger

prefix = config.get("REDIS_KEY_PREFIX")


def apply_service(name: str, spec: dict):
    """
    spec:{
        "servers":[
            "http://127.0.0.1:80"
        ]
    }
    """
    svc_prefix = "{}/ingress/http/services/{}".format(prefix, name)
    # servers
    servers: List[str] = spec.get("servers", [])
    servers_prefix = "{}/loadBalancer/servers".format(svc_prefix)
    servers_match = "{}/*".format(servers_prefix)
    cursor, key_list = redis_client.scan(0, servers_match)
    for key in [x.decode() for x in key_list]:
        redis_client.delete(key)
    while cursor != 0:
        cursor, key_list = redis_client.scan(cursor, servers_match)
        for key in [x.decode() for x in key_list]:
            redis_client.delete(key)
    for index, url in enumerate(servers):
        key = "{}/{}/url".format(servers_prefix, index)
        redis_client.set(key, url)


def get_service_info(name) -> dict:
    svc_prefix = "{}/ingress/http/services/{}".format(prefix, name)
    key_list = redis_client.keys("{}/*".format(svc_prefix))
    if not key_list:
        return {
            "servers": []
        }
    # servers
    servers = []
    servers_prefix = "{}/loadBalancer/servers".format(svc_prefix)
    servers_match = "{}/*".format(servers_prefix)
    cursor, key_list = redis_client.scan(0, servers_match)
    for key in [x.decode() for x in key_list]:
        bts = redis_client.get(key)
        if bts:
            servers.append(bts.decode())
    while cursor != 0:
        cursor, key_list = redis_client.scan(cursor, servers_match)
        for key in [x.decode() for x in key_list]:
            bts = redis_client.get(key)
            if bts:
                servers.append(bts.decode())
    return {
        "servers": servers
    }


def get_service_servers_info(name) -> list:
    result = []
    servers = get_service_info(name).get("servers", [])
    for server in servers:
        addr, port = server.replace("http://", "").split(":")
        result.append({
            "ip": addr,
            "port": port
        })
    return result


def delete_service(name: str):
    svc_prefix = "{}/ingress/http/services/{}".format(prefix, name)
    # servers
    servers_prefix = "{}/loadBalancer/servers".format(svc_prefix)
    servers_match = "{}/*".format(servers_prefix)
    cursor, key_list = redis_client.scan(0, servers_match)
    for key in [x.decode() for x in key_list]:
        redis_client.delete(key)
    while cursor != 0:
        cursor, key_list = redis_client.scan(cursor, servers_match)
        for key in [x.decode() for x in key_list]:
            redis_client.delete(key)


def apply_router(name: str, spec: dict):
    """
    spes:{
        "service":"demo-svc",
        "rule":"PathPrefix(`/`)"
    }
    """
    router_prefix = "{}/ingress/http/routers/{}".format(prefix, name)
    # entrypoints
    entry_key = "{}/entrypoints/0".format(router_prefix)
    redis_client.set(entry_key, "http80")  # hard code by operator
    # rule
    rule: str = spec.get("rule")
    rule_key = "{}/rule".format(router_prefix)
    redis_client.set(rule_key, rule.strip())
    # service
    service: str = spec.get("service")
    service_key = "{}/service".format(router_prefix)
    redis_client.set(service_key, service)


def get_router_info(name: str):
    router_prefix = "{}/ingress/http/routers/{}".format(prefix, name)
    key_list = redis_client.keys("{}/*".format(router_prefix))
    if not key_list:
        return None
    # rule
    rule_key = "{}/rule".format(router_prefix)
    bts: bytes = redis_client.get(rule_key)
    rule = bts.decode() if bts else None
    # service
    service_key = "{}/service".format(router_prefix)
    bts: bytes = redis_client.get(service_key)
    service = bts.decode() if bts else None
    return {
        "rule": rule,
        "service": service
    }


def delete_router(name: str):
    router_prefix = "{}/ingress/http/routers/{}".format(prefix, name)
    # entrypoints
    entry_key = "{}/entrypoints/0".format(router_prefix)
    redis_client.delete(entry_key)
    # rule
    rule_key = "{}/rule".format(router_prefix)
    redis_client.delete(rule_key)
    # service
    service_key = "{}/service".format(router_prefix)
    redis_client.delete(service_key)
