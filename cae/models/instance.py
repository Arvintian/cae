
from cae.config import config
from cae.models import redis_client
from docker.models.containers import Container
import json

prefix = config.get("REDIS_KEY_PREFIX")
_instance_id_key = "{}/instanceid".format(prefix)


def get_instance(key) -> dict:
    _key = "{}/instance/{}".format(prefix, key)
    bts = redis_client.get(_key)
    if bts:
        return json.loads(bts)
    return None


def get_instance_by_name(name) -> dict:
    bts: bytes = redis_client.hget(_instance_id_key, name)
    if not bts:
        return None
    instance_id = bts.decode()
    return get_instance(instance_id)


def put_instance(key, ins: dict):
    _key = "{}/instance/{}".format(prefix, key)
    redis_client.hset(_instance_id_key, ins.get("name"), key)
    redis_client.set(_key, json.dumps(ins))


def del_instance(key):
    _key = "{}/instance/{}".format(prefix, key)
    ins = get_instance(key)
    redis_client.hdel(_instance_id_key, ins.get("name"))
    redis_client.delete(_key)


def inspec_to_info(item: Container) -> dict:
    attrs: dict = item.attrs
    network_setting: dict = attrs.get("NetworkSettings", {}).get("Networks", {}).get(config.get("DOCKER_NETWORK"), {})
    ip_addr = network_setting.get("IPAddress", None)
    if not ip_addr:
        ipam_config: dict = network_setting.get("IPAMConfig", {})
        ip_addr = ipam_config.get("IPv4Address")
    return {
        "Id": attrs.get("Id"),
        "Name": item.name,
        "Labels": item.labels,
        "Image": attrs.get("Config", {}).get("Image"),
        "IP": ip_addr,
        "Status": item.status,
        "Created": attrs.get("Created"),
    }
