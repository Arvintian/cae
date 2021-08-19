from typing import List
from cae.config import config
from cae.models import redis_client
import ipaddress

prefix = config.get("REDIS_KEY_PREFIX")
_ipam_id_key = "{}/ipam".format(prefix)


def reserve_ip(ip: str, container_id: str):
    redis_client.hset(_ipam_id_key, ip, container_id)


def release_ip(ip: str):
    redis_client.hdel(_ipam_id_key, ip)


def assign_ip():
    blocks = config.get("DOCKER_NETWORK_BLOCKS", "").split(",")
    pools: List[ipaddress.IPv4Network] = []
    for block in blocks:
        pool = ipaddress.ip_network(block)
        pools.append(pool)
    for pool in pools:
        for addr in pool.hosts():
            ip = str(addr)
            if not redis_client.hexists(_ipam_id_key, ip):
                return ip
    raise Exception("assign ip fail")
