import traceback
from docker.models.containers import Container
import docker.utils as dockerutils
from cae.config import channel_config as config
from cae.channel.utils import ObjDict
from cae.services import docker_service
from cae.models import instance
from pretty_logging import pretty_logger
from .proxy import ProxyServer
from .direct import DirectServer
from .exec import ExecServer
from typing import List
import shutil
import tempfile
import os
import io
import tarfile
import socket
import paramiko


class InteractiveServer:
    _sentinel = object()

    def __init__(self, client):
        self.client = client
        self.closed = False
        self.dc = docker_service.get_docker_client()

    def __str__(self):
        return "interactive {}".format(self.client)

    def proxy(self, container: Container):
        """
        Proxy session
        """
        instance_info = instance.inspec_to_info(container)
        asset = ObjDict()
        asset.update({
            "ip": instance_info.get("IP"),
            "ssh_port": 22,
        })
        system_user = ObjDict()
        system_user.update({
            "username": self.client.user.get("username"),
            "password": None,
            "private_key": paramiko.RSAKey.from_private_key_file(filename=config["HOST_PRIVATE_KEY"]),
            "protocol": "ssh"
        })
        forwarder = ProxyServer(self.client, asset, system_user)
        forwarder.proxy()

    def exec(self, container: Container):
        """
        Proxy exec
        """
        instance_info = instance.inspec_to_info(container)
        asset = ObjDict()
        asset.update({
            "ip": instance_info.get("IP"),
            "ssh_port": 22,
        })
        system_user = ObjDict()
        system_user.update({
            "username": self.client.user.get("username"),
            "password": None,
            "private_key": paramiko.RSAKey.from_private_key_file(filename=config["HOST_PRIVATE_KEY"]),
            "protocol": "ssh"
        })
        forwarder = ExecServer(self.client, asset, system_user, container)
        forwarder.proxy()

    def tunnel(self, container: Container):
        """
        Proxy tunnel
        """
        asset = ObjDict()
        asset.update({
            "origin": self.client.request.meta.get("origin"),
        })
        system_user = ObjDict()
        system_user.update({
            "destination": self.client.request.meta.get("destination"),
        })

        # check destination is instance self
        dest: tuple = self.client.request.meta.get("destination")
        instance_info = instance.inspec_to_info(container)
        instance_ip = instance_info.get("IP")
        if dest[0] != instance_ip:
            pretty_logger.error("{} tunnel destination ip {} error".format(container.id, dest[0]))
            return

        forwarder = DirectServer(self.client, asset, system_user)
        forwarder.proxy()

    def interact(self, kind: str):
        """
        Entrance
        """
        try:
            instance_id = self.client.user.get("instance_id")
            cs: List[Container] = self.dc.containers.list(filters={
                "label": ["cae.app=true"],
                "id": instance_id
            })
            if not cs:
                raise Exception("not found instance {}".format(instance_id))
            container: Container = cs[0]

            is_have_sshd = check_container_sshd(container)

            if is_have_sshd:
                public_keys = "\n".join(self.client.user.get("auth_keys", []))
                with open(config["HOST_PUBLIC_KEY"]) as fd:
                    public_keys = "{}\n{}\n".format(public_keys, fd.read())

                username = self.client.user.get("username")
                ensure_public_key(container, username, public_keys)

        except Exception as e:
            pretty_logger.error(traceback.format_exc())
            self.close()
            return

        if kind == "session":
            try:
                if is_have_sshd:
                    self.proxy(container)
                else:
                    self.exec(container)
            except socket.error as e:
                pretty_logger.error("Socket error: {}".format(e))
            except Exception as e:
                pretty_logger.error(traceback.format_exc())
        elif is_have_sshd and kind == "direct-tcpip":
            try:
                self.tunnel(container)
            except socket.error as e:
                pretty_logger.error("Socket error: {}".format(e))
            except Exception as e:
                pretty_logger.error(traceback.format_exc())
        else:
            pretty_logger.error("not support interact kind {}".format(kind))

        self.close()

    def close(self):
        pretty_logger.info("Interactive server server close: {}".format(self))
        self.closed = True


def ensure_public_key(container: Container, username, public_key):

    userinfo = get_user_info(container, username)

    # create tar
    data_dir = make_tree([".ssh"], [(".ssh/authorized_keys", public_key, 0o644)])
    current_bts = dockerutils.tar(data_dir)

    # update tarinfo uid/gid
    out_bts = io.BytesIO()
    out_tar = tarfile.open(mode="w", fileobj=out_bts)
    with tarfile.open(fileobj=current_bts) as tarobj:
        for info in tarobj:
            info.uid = int(userinfo.get("uid"))
            info.gid = int(userinfo.get("gid"))
            out_tar.addfile(info, fileobj=tarobj.extractfile(info.name))
    out_tar.close()

    # put tar
    out_bts.seek(0)
    container.put_archive(path=userinfo.get("home"), data=out_bts)

    # clean tmp
    current_bts.close()
    out_bts.close()
    shutil.rmtree(data_dir)


def check_container_sshd(container: Container) -> bool:
    try:
        bts, stat = container.get_archive("/var/run/sshd.pid")
        pretty_logger.info("{} sshd.pid {}".format(container.id, stat))
        if stat.get("size") < 1:
            raise Exception("container sshd.pid file if none {}".format(container.id))
        return True
    except Exception as e:
        pretty_logger.error("{}".format(e))
        return False


def get_user_info(container: Container, username) -> dict:
    bts, stat = container.get_archive("/etc/passwd")
    if stat.get("size") < 1:
        raise Exception("container passwd file if none {}".format(container.id))
    passwd_tar = io.BytesIO()
    for chunk in bts:
        passwd_tar.write(chunk)
    passwd_tar.seek(0)
    with tarfile.open(fileobj=passwd_tar) as tar_obj:
        for item in tar_obj.extractfile("passwd").readlines():
            line = item.decode().strip().split(":")
            if line[0] == username:
                passwd_tar.close()
                return {
                    "username": username,
                    "uid": line[2],
                    "gid": line[3],
                    "home": line[-2],
                    "shell": line[-1]
                }
    passwd_tar.close()
    raise Exception("not found user info {} {}".format(container.id, username))


def make_tree(dirs, files):
    base = tempfile.mkdtemp()

    for path in dirs:
        the_path = os.path.join(base, path)
        os.makedirs(the_path)

    for path, data, mode in files:
        the_path = os.path.join(base, path)
        with open(the_path, 'w') as f:
            f.write(data)
        os.chmod(the_path, mode)

    return base
