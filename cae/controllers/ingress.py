from madara.wrappers import Request
from madara.blueprints import Blueprint
from cae.repositorys.validation import use_args
from cae.models import ingress, redis_client
from cae.config import config
from webargs import fields

bp_ingress = Blueprint("bp_ingress")


@bp_ingress.route("/service/apply", methods=["POST"])
@use_args({
    "name": fields.Str(required=True),
    "servers": fields.List(fields.Nested({
        "ip": fields.IP(required=True),
        "port": fields.Integer(required=True),
    }), required=True)
}, location="json")
def apply_service(request: Request, json_args: dict):
    spec = {}
    name = json_args.get("name")
    # servers
    servers = []
    for server in json_args.get("servers"):
        servers.append("http://{}:{}".format(server.get("ip"), server.get("port")))
    spec.update({
        "servers": servers
    })
    ingress.apply_service(name, spec)
    return {
        "code": 200,
        "result": "success"
    }


@bp_ingress.route("/service", methods=["GET"])
@bp_ingress.route("/service/<service_name>", methods=["GET"])
@use_args({"service_name": fields.Str(required=False)}, location="view_args")
def get_service(request: Request, view_args, service_name=None):
    result = None
    if service_name:
        spec = ingress.get_service_servers_info(service_name)
        if not spec:
            raise Exception("not found service {}".format(service_name))
        result = {
            "name": service_name,
            "servers": spec
        }
    else:
        result = []
        key_match = "{}/ingress/http/services/*/loadBalancer/servers/0/url".format(config.get("REDIS_KEY_PREFIX"))
        cursor, key_list = redis_client.scan(0, key_match)
        for key in [x.decode() for x in key_list]:
            # cae/ingress/http/routers/<service_name>/loadBalancer/servers/0/url
            service_name = key.split("/")[-5]
            if service_name == "cae-placeholder":
                continue
            result.append({
                "name": service_name,
                "servers": ingress.get_service_servers_info(service_name)
            })
        while cursor != 0:
            cursor, key_list = redis_client.scan(cursor, key_match)
            for key in [x.decode() for x in key_list]:
                service_name = key.split("/")[-5]
                if service_name == "cae-placeholder":
                    continue
                result.append({
                    "name": service_name,
                    "servers": ingress.get_service_servers_info(service_name)
                })
    return {
        "code": 200,
        "result": result
    }


@bp_ingress.route("/service/<service_name>", methods=["DELETE"])
@use_args({"service_name": fields.Str(required=True)}, location="view_args")
def service_del(request: Request, view_args, service_name):
    if not ingress.get_service_info(service_name):
        raise Exception("not found service {}".format(service_name))
    ingress.delete_service(service_name)
    return {
        "code": 200,
        "result": "success"
    }


@bp_ingress.route("/router/apply", methods=["POST"])
@use_args({
    "name": fields.Str(required=True),
    "rule": fields.Str(required=True),
    "service": fields.Str(required=True)
}, location="json")
def apply_router(request: Request, json_args: dict):
    spec = {}
    name = json_args.get("name")
    # service
    service = json_args.get("service")
    if not ingress.get_service_info(service):
        raise Exception("args error service {} not found".format(service))
    spec.update({
        "service": service
    })
    # rule
    spec.update({
        "rule": json_args.get("rule")
    })
    # apply
    ingress.apply_router(name, spec)
    return {
        "code": 200,
        "result": "success"
    }


@bp_ingress.route("/router", methods=["GET"])
@bp_ingress.route("/router/<router_name>", methods=["GET"])
@use_args({"router_name": fields.Str(required=False)}, location="view_args")
def fetch_router(request: Request, view_args: dict, router_name=None):
    result = None
    if router_name:
        spec: dict = ingress.get_router_info(router_name)
        if not spec:
            raise Exception("not found router {}".format(router_name))
        result = {
            "name": router_name,
            **spec
        }
    else:
        result = []
        key_match = "{}/ingress/http/routers/*/rule".format(config.get("REDIS_KEY_PREFIX"))
        cursor, key_list = redis_client.scan(0, key_match)
        for key in [x.decode() for x in key_list]:
            # cae/ingress/http/routers/<router_name>/rule
            router_name = key.split("/")[-2]
            spec = ingress.get_router_info(router_name)
            result.append({
                "name": router_name,
                **spec
            })
        while cursor != 0:
            cursor, key_list = redis_client.scan(cursor, key_match)
            for key in [x.decode() for x in key_list]:
                # cae/ingress/http/routers/<router_name>/rule
                router_name = key.split("/")[-2]
                spec = ingress.get_router_info(router_name)
                result.append({
                    "name": router_name,
                    **spec
                })
    return {
        "code": 200,
        "result": result
    }


@bp_ingress.route("/router/<router_name>", methods=["DELETE"])
@use_args({"router_name": fields.Str(required=True)}, location="view_args")
def router_del(request: Request, view_args: dict, router_name: str):
    ingress.delete_router(router_name)
    return {
        "code": 200,
        "result": "success"
    }
