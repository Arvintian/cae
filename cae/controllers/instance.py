from docker.models.containers import Container, _create_container_args
from docker.errors import ImageNotFound
from typing import List
from madara.wrappers import Request
from madara.blueprints import Blueprint
from cae.services import docker_service
from cae.config import config
from cae.repositorys.validation import use_args
from cae.models import instance as instance_model
from cae.models import network as network_model
from webargs import fields

bp_instance = Blueprint("bp_instance")

dc = docker_service.get_docker_client()


@bp_instance.route("/list", methods=["GET"])
def list_instance(request: Request):
    instance_filters = {
        "label": ["cae.app=true"]
    }
    cs: List[Container] = dc.containers.list(all=True, filters=instance_filters)
    result = []
    for item in cs:
        result.append(instance_model.inspec_to_info(item))
    return {
        "code": 200,
        "result": result
    }


@bp_instance.route("/info/<instance_id>", methods=["GET"])
def info_instance(request: Request, instance_id):
    instance_filters = {
        "label": ["cae.app=true"],
        "id": instance_id
    }
    cs: List[Container] = dc.containers.list(all=True, filters=instance_filters)
    if not cs:
        raise Exception("not found instance {}".format(instance_id))
    container: Container = cs[0]

    info = {
        "inspect": instance_model.inspec_to_info(container),
        "model": instance_model.get_instance(instance_id)
    }

    return {
        "code": 200,
        "result": info
    }


@bp_instance.route("/create", methods=["POST"])
@use_args({
    "name": fields.Str(required=True),
    "desc": fields.Str(required=True),
    "image": fields.Str(required=True),
    "auth_keys": fields.List(fields.Str, required=True),
    "envs": fields.List(fields.Nested({
        "key": fields.Str(required=True),
        "value": fields.Str(required=True)
    }), required=False),
}, location="json")
def create_instance(request: Request, json_args: dict):
    if not json_args.get("name") or not json_args.get("image"):
        raise Exception("bad request, args error")
    # run spec
    spec = {
        "name": json_args.get("name"),
        "image": json_args.get("image"),
        "version": dc.version,
        "hostname": json_args.get("name"),
        "labels": {
            "cae.app": "true",
            "cae.instance": json_args.get("name"),
        },
        "environment": {item["key"]: item["value"] for item in json_args.get("envs", [])},
        "detach": True,
        "network": config.get("DOCKER_NETWORK"),
        "restart_policy": {
            "Name": "unless-stopped"
        },
        "cap_add": ["SYSLOG", "SYS_PTRACE"],  # for rsyslog
    }

    ip_addr = network_model.assign_ip()

    # create container
    create_args = _create_container_args(spec)
    networking_config = dc.api.create_networking_config({
        config.get("DOCKER_NETWORK"): dc.api.create_endpoint_config(
            ipv4_address=ip_addr,
        )
    })
    # set container static ip
    create_args.update({
        "networking_config": networking_config
    })
    container_id = dc.api.create_container(**create_args)
    container: Container = dc.containers.prepare_model(dc.api.inspect_container(container_id))

    # save model
    record = {}
    record.update(json_args)
    record.update({
        "id": container.id,
        "ip": ip_addr
    })
    instance_model.put_instance(container.id, record)
    network_model.reserve_ip(ip_addr, container.id)

    # start container
    container.start()
    return {
        "code": 200,
        "result": instance_model.inspec_to_info(container)
    }


@bp_instance.route("/update/<instance_id>", methods=["PUT"])
@use_args({
    "desc": fields.Str(required=True),
    "auth_keys": fields.List(fields.Str, required=True)
}, location="json")
def update_instance(request: Request, json_args: dict, instance_id):
    model = instance_model.get_instance(instance_id)
    if not model:
        raise Exception("not found instance {}".format(instance_id))

    if json_args.get("desc"):
        model.update({
            "desc": json_args.get("desc")
        })

    if json_args.get("auth_keys"):
        model.update({
            "auth_keys": json_args.get("auth_keys")
        })

    # update model
    instance_model.put_instance(instance_id, model)

    return {
        "code": 200,
        "result": "success"
    }


@bp_instance.route("/action/<instance_id>", methods=["PUT"])
@use_args({
    "action": fields.Str(required=True),
}, location="json")
def action_instance(request: Request, json_args: dict, instance_id):
    instance_filters = {
        "label": ["cae.app=true"],
        "id": instance_id
    }
    cs: List[Container] = dc.containers.list(all=True, filters=instance_filters)
    if not cs:
        raise Exception("not found instance {}".format(instance_id))
    container: Container = cs[0]

    action = json_args.get("action")
    if not action in ["restart", "start", "stop"]:
        raise Exception("not support action {}".format(action))

    action_func = getattr(container, action)
    action_func()

    return {
        "code": 200,
        "result": "success"
    }


@bp_instance.route("/image/<instance_id>", methods=["PUT"])
@use_args({
    "repository": fields.Str(required=True),
    "tag": fields.Str(required=True),
    "comment": fields.Str(required=True),
}, location="json")
def image_instance(request: Request, json_args: dict, instance_id):
    instance_filters = {
        "label": ["cae.app=true"],
        "id": instance_id
    }
    cs: List[Container] = dc.containers.list(all=True, filters=instance_filters)
    if not cs:
        raise Exception("not found instance {}".format(instance_id))
    container: Container = cs[0]

    # image exist
    try:
        image_name = "{}:{}".format(json_args.get("repository"), json_args.get("tag"))
        exist_image = dc.images.get(image_name)
    except ImageNotFound:
        exist_image = None

    if exist_image:
        raise Exception("image tag exsit")

    # commit image
    conf = {
        "Labels": {
            "cae.image": "true",
        }
    }
    commit_args = {
        "repository": json_args.get("repository"),
        "tag": json_args.get("tag"),
        "message": json_args.get("comment"),
        "conf": conf
    }
    container.commit(**commit_args)

    return {
        "code": 200,
        "result": "success"
    }


@bp_instance.route("/delete/<instance_id>", methods=["DELETE"])
def delete_instance(request: Request, instance_id):
    instance_filters = {
        "label": ["cae.app=true"],
        "id": instance_id
    }
    cs: List[Container] = dc.containers.list(all=True, filters=instance_filters)
    if not cs:
        raise Exception("not found instance {}".format(instance_id))
    container: Container = cs[0]

    container_info: dict = instance_model.inspec_to_info(container)

    # remove container
    container.remove(force=True)

    # delete model
    instance_model.del_instance(instance_id)
    network_model.release_ip(container_info.get("IP"))

    return {
        "code": 200,
        "result": "success"
    }
