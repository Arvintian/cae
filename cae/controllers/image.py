from typing import List
from madara.wrappers import Request
from madara.blueprints import Blueprint
from docker.models.images import Image
from docker.errors import ImageNotFound
from cae.services import docker_service
from cae.repositorys.validation import use_args
from webargs import fields

bp_image = Blueprint("bp_image")

dc = docker_service.get_docker_client()


@bp_image.route("/list", methods=["GET"])
def list_image(request: Request):
    image_filters = {
        "label": ["cae.image=true"]
    }
    images: List[Image] = dc.images.list(filters=image_filters)
    result = []
    for image in images:
        for tag in image.tags:
            name, the_tag = tag.split(":")
            result.append({
                "name": name,
                "tag": the_tag,
                "comment": image.attrs.get("Comment"),
                "created": image.attrs.get("Created")
            })
    return {
        "code": 200,
        "result": result
    }


@bp_image.route("/delete", methods=["PUT"])
@use_args({
    "repository": fields.Str(required=True),
    "tag": fields.Str(required=True),
}, location="json")
def delete_image(request: Request, json_args: dict):
    image_name = "{}:{}".format(json_args.get("repository"), json_args.get("tag"))

    # check exist
    try:
        exist_image: Image = dc.images.get(image_name)
    except ImageNotFound:
        exist_image = None
    if not exist_image:
        raise Exception("image not found")

    # remove image
    dc.images.remove(image=image_name)

    return {
        "code": 200,
        "result": "success"
    }
