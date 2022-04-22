import paramiko
import threading
from pretty_logging import pretty_logger
from cae.models import instance
from cae.channel.utils import parser_public_key


class SSHInterface(paramiko.ServerInterface):
    """
    使用paramiko提供的接口实现ssh server.

    More see paramiko ssh server demo
    https://github.com/paramiko/paramiko/blob/master/demos/demo_server.py
    """

    def __init__(self, connection):
        self.connection = connection
        self.event = threading.Event()
        self.user = None

    def enable_auth_gssapi(self):
        return False

    def get_allowed_auths(self, username):
        supported = []
        supported.append("publickey")
        return ",".join(supported)

    def check_auth_none(self, username):
        return paramiko.AUTH_FAILED

    def check_auth_password(self, username, password):
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        key = key.get_base64()
        user = self.validate_auth(username, public_key=key)

        if not user:
            pretty_logger.debug("Public key auth <%s> failed, try to password" % username)
            return paramiko.AUTH_FAILED
        else:
            pretty_logger.info("Public key auth <%s> success" % username)
            return paramiko.AUTH_SUCCESSFUL

    def validate_auth(self, username: str, password="", public_key=""):
        remote_addr = self.connection.addr[0]

        ins_name, ins_user = username.split(":")
        if not ins_name or not ins_user:
            pretty_logger.info("validate username fail {} {}".format(username, remote_addr))
            return None

        # instance info
        ins: dict = instance.get_instance_by_name(ins_name)
        if not ins:
            pretty_logger.info("varlidate instance not found {} {}".format(username, remote_addr))
            return None

        # auth key
        auth_key = ""
        for key in ins.get("auth_keys", []):
            the_pub_key = parser_public_key(key)
            if the_pub_key == public_key:
                auth_key = key
                break
        if not auth_key:
            pretty_logger.info("validate public key not found {} {}".format(username, remote_addr))
            return None

        # instance user
        user = {
            "username": ins_user,
            "instance_id": ins.get("id"),
            "auth_keys": ins.get("auth_keys"),
            "auth_key": auth_key
        }
        if user:
            self.connection.user = user

        return user

    def check_channel_direct_tcpip_request(self, chanid, origin, destination):
        pretty_logger.info("Check channel direct tcpip request: %d %s %s" % (chanid, origin, destination))
        client = self.connection.new_client(chanid)
        client.request.kind = 'direct-tcpip'
        client.request.type = 'direct-tcpip'
        client.request.meta.update({
            'origin': origin, 'destination': destination
        })
        self.event.set()
        return 0

    def check_port_forward_request(self, address, port):
        pretty_logger.info("Check channel port forward request: %s %s" % (address, port))
        self.event.set()
        return False

    def check_channel_request(self, kind, chanid):
        pretty_logger.info("Check channel request: %s %d" % (kind, chanid))
        client = self.connection.new_client(chanid)
        client.request.kind = kind
        return paramiko.OPEN_SUCCEEDED

    def check_channel_env_request(self, channel, name, value):
        pretty_logger.info("Check channel env request: %s, %s, %s" % (channel.get_id(), name, value))
        client = self.connection.get_client(channel)
        client.request.meta['env'][name] = value
        return False

    def check_channel_exec_request(self, channel, command):
        pretty_logger.info("Check channel exec request:  `%s`" % command)
        client = self.connection.get_client(channel)
        client.request.type = 'exec'
        client.request.meta.update({
            'command': command
        })
        self.event.set()
        return True

    def check_channel_forward_agent_request(self, channel):
        pretty_logger.info("Check channel forward agent request: %s" % channel)
        client = self.connection.get_client(channel)
        client.request.meta['forward-agent'] = True
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        pretty_logger.info("Check channel pty request: %s %s %s %s %s" % (term, width, height, pixelwidth, pixelheight))
        client = self.connection.get_client(channel)
        client.request.type = 'pty'
        client.request.meta.update({
            'term': term, 'width': width,
            'height': height, 'pixelwidth': pixelwidth,
            'pixelheight': pixelheight,
        })
        self.event.set()
        return True

    def check_channel_shell_request(self, channel):
        pretty_logger.info("Check channel shell request: %s" % channel.get_id())
        client = self.connection.get_client(channel)
        client.request.meta['shell'] = True
        return True

    def check_channel_subsystem_request(self, channel, name):
        pretty_logger.info("Check channel subsystem request: %s" % name)
        client = self.connection.get_client(channel)
        client.request.type = 'subsystem'
        client.request.meta['subsystem'] = name
        self.event.set()
        return super(SSHInterface, self).check_channel_subsystem_request(channel, name)

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        client = self.connection.get_client(channel)
        client.request.meta.update({
            'width': width,
            'height': height,
            'pixelwidth': pixelwidth,
            'pixelheight': pixelheight,
        })
        client.change_size_evt.set()
        return True

    def check_channel_x11_request(self, channel, single_connection, auth_protocol, auth_cookie, screen_number):
        pretty_logger.info("Check channel x11 request %s %s %s %s" % (single_connection, auth_protocol, auth_cookie, screen_number))
        client = self.connection.get_client(channel)
        # client.request_x11_event.set()
        client.request.meta.update({
            'single_connection': single_connection,
            'auth_protocol': auth_protocol,
            'auth_cookie': auth_cookie,
            'screen_number': screen_number,
        })
        return False

    def get_banner(self):
        return None, None
