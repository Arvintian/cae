from cae.config import channel_config as config
from cae.channel.utils import get_private_key_fingerprint, wrap_with_line_feed, wrap_with_warning, SelectEvent
from pretty_logging import pretty_logger
import paramiko
import uuid
import datetime
import selectors
import socket


class ProxyServer:
    def __init__(self, client, asset, system_user):
        """
        asset:{
            ip string
            ssh_port int
        }
        system_user:{
            username string
            password string
            private_key string
            protocol:"ssh" enum
        }
        """
        self.client = client
        self.asset = asset
        self.system_user = system_user
        self.server = None
        self.connecting = True

    def proxy(self):
        self.server = self.get_server_conn_from_cache()
        if not self.server:
            self.server = self.get_server_conn()
        if self.server is None:
            return
        if self.client.closed:
            self.server.close()
            return
        session = Session.new_session(self.client, self.server)
        if not session:
            msg = "Connect with api server failed"
            pretty_logger.error(msg)
            self.client.send_unicode(msg)
            self.server.close()
            return

        try:
            session.bridge()
        finally:
            Session.remove_session(session.id)
            self.server.close()
            msg = 'Session end, total {} now'.format(
                len(Session.sessions),
            )
            pretty_logger.info(msg)

    def get_server_conn_from_cache(self):
        server = None
        if self.system_user.protocol == 'ssh':
            server = self.get_ssh_server_conn(cache=True)
        return server

    def get_server_conn(self):
        if self.system_user.protocol == 'ssh':
            pretty_logger.info("Connect to {}:{}".format(self.asset.ip, self.asset.ssh_port))
            server = self.get_ssh_server_conn()
        else:
            server = None
        self.client.send(b'\r\n')
        self.connecting = False
        return server

    def get_ssh_server_conn(self, cache=False):
        request = self.client.request
        term = request.meta.get('term', 'xterm')
        width = request.meta.get('width', 80)
        height = request.meta.get('height', 24)

        if cache:
            conn = SSHConnection.new_connection_from_cache(self.client.user, self.asset, self.system_user)
            if not conn or not conn.is_active:
                return None
            else:
                # 采用复用连接创建session时，系统用户用户名如果为空，创建session-400
                self.system_user = conn.system_user
        else:
            conn = SSHConnection.new_connection(self.client.user, self.asset, self.system_user)
        chan = conn.get_channel(term=term, width=width, height=height)
        if not chan:
            self.client.send_unicode(wrap_with_warning(wrap_with_line_feed(conn.error, before=1, after=0)))
            server = None
        else:
            server = Server(chan, conn, self.asset, self.system_user)
        return server


class SSHConnection:
    connections = {}

    @staticmethod
    def make_key(user, asset, system_user):
        key = "{}_{}_{}".format(user.username, asset.ip, system_user.username)
        return key

    @classmethod
    def new_connection_from_cache(cls, user, asset, system_user):
        key = cls.make_key(user, asset, system_user)
        connection = cls.connections.get(key)
        if not connection:
            return None
        if not connection.is_active:
            cls.connections.pop(key, None)
            return None
        connection.ref += 1
        return connection

    @classmethod
    def set_connection_to_cache(cls, conn):
        key = cls.make_key(conn.user, conn.asset, conn.system_user)
        cls.connections[key] = conn

    @classmethod
    def new_connection(cls, user, asset, system_user):
        connection = cls.new_connection_from_cache(user, asset, system_user)

        if connection:
            pretty_logger.info("Reuse connection: {}->{}@{}".format(user.username, asset.ip, system_user.username))
            return connection
        connection = cls(user, asset, system_user)
        connection.connect()
        if connection.is_active:
            cls.set_connection_to_cache(connection)
        return connection

    @classmethod
    def remove_ssh_connection(cls, conn):
        key = "{}_{}_{}".format(conn.user.username, conn.asset.ip, conn.system_user.username)
        cls.connections.pop(key, None)

    def __init__(self, user, asset, system_user):
        """
        user:{
            username
        }
        asset:{
            ip
            ssh_port
        }
        system_user:{
            username
            password
            private_key
        }
        """
        self.user = user
        self.asset = asset
        self.system_user = system_user
        self.client = None
        self.transport = None
        self.sock = None
        self.error = ""
        self.ref = 1

    def connect(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        sock = None
        error = ''

        asset = self.asset
        system_user = self.system_user
        try:
            try:
                ssh.connect(
                    asset.ip, port=asset.ssh_port, username=system_user.username,
                    password=system_user.password, pkey=system_user.private_key,
                    timeout=config['SSH_TIMEOUT'],
                    compress=False, auth_timeout=config['SSH_TIMEOUT'],
                    look_for_keys=False, sock=sock
                )
            except paramiko.AuthenticationException:
                # 思科设备不支持秘钥登陆，提供秘钥，必然失败
                ssh.connect(
                    asset.ip, port=asset.ssh_port, username=system_user.username,
                    password=system_user.password, timeout=config['SSH_TIMEOUT'],
                    compress=False, auth_timeout=config['SSH_TIMEOUT'],
                    look_for_keys=False, sock=sock, allow_agent=False,
                )
            transport = ssh.get_transport()
            transport.set_keepalive(60)
            self.transport = transport
        except Exception as e:
            password_short = "None"
            key_fingerprint = "None"
            if system_user.password:
                password_short = system_user.password[:5] + (len(system_user.password) - 5) * '*'
            if system_user.private_key:
                key_fingerprint = get_private_key_fingerprint(system_user.private_key)
            msg = "Connect {}@{}:{} auth failed, password: {}, key: {}".format(system_user.username, asset.ip, asset.ssh_port, password_short, key_fingerprint,)
            pretty_logger.error(msg)
            error += '\r\n' + str(e) if error else str(e)
            ssh, sock = None, None
            raise e
        self.client = ssh
        self.sock = ssh
        self.error = error

    def reconnect_if_need(self):
        if not self.is_active:
            self.connect()

        if self.is_active:
            return True
        return False

    def get_transport(self):
        if self.reconnect_if_need():
            return self.transport
        return None

    def get_channel(self, term="xterm", width=80, height=24):
        if self.reconnect_if_need():
            chan = self.client.invoke_shell(term, width=width, height=height)
            return chan
        else:
            return None

    def get_sftp(self):
        if self.reconnect_if_need():
            return self.client.open_sftp()
        else:
            return None

    @property
    def is_active(self):
        return self.transport and self.transport.is_active()

    def close(self):
        if self.ref > 1:
            self.ref -= 1
            msg = "Connection ref -1: {}->{}@{}. {}".format(self.user.username, self.asset.ip, self.system_user.username, self.ref)
            pretty_logger.info(msg)
            return
        self.__class__.remove_ssh_connection(self)
        try:
            self.client.close()
            if self.sock:
                self.sock.close()
        except Exception as e:
            pretty_logger.error("Close connection error: {}".format(e))

        msg = "Close connection: {}->{}@{}. Total connections live: {}".format(self.user.username,
                                                                               self.asset.ip, self.system_user.username, len(self.connections))
        pretty_logger.info(msg)


class Server(object):

    def __init__(self, chan, conn, asset, system_user):
        self.id = str(uuid.uuid4())
        self.chan = chan
        self.conn = conn
        self.asset = asset
        self.system_user = system_user

    def fileno(self):
        return self.chan.fileno()

    def send(self, b):
        try:
            return self.chan.send(b)
        except (OSError, EOFError, socket.error) as e:
            pretty_logger.error('Send to client {} error: {}'.format(self, e))
            return 0

    def send_unicode(self, s):
        b = s.encode()
        self.send(b)

    @property
    def closed(self):
        return self.chan.closed

    def recv(self, size):
        return self.chan.recv(size)

    def close(self):
        pretty_logger.info("Server {} close".format(self))
        if self.chan:
            self.chan.close()
        if self.conn:
            self.conn.close()
        return

    def __getattr__(self, item):
        return getattr(self.chan, item)

    def __str__(self):
        return "server %s:%s" % (self.asset.ip, self.asset.ssh_port)


class Session:
    sessions = {}

    def __init__(self, client, server):
        self.id = str(uuid.uuid4())
        self.client = client  # Master of the session, it's a client sock
        self.server = server  # Server channel
        self.date_start = datetime.datetime.utcnow()
        self.date_end = None
        self.is_finished = False
        self.closed = False
        self.sel = selectors.DefaultSelector()
        self.stop_evt = SelectEvent()
        self.date_last_active = datetime.datetime.utcnow()

    @classmethod
    def new_session(cls, client, server):
        session = cls(client, server)
        cls.sessions[session.id] = session
        return session

    @classmethod
    def get_session(cls, sid):
        return cls.sessions.get(sid)

    @classmethod
    def remove_session(cls, sid):
        session = cls.get_session(sid)
        if session:
            session.close()
            cls.sessions.pop(sid, None)

    def bridge(self):
        """
        Bridge clients with server
        :return:
        """
        pretty_logger.info("Start bridge session: {}".format(self.id))
        self.sel.register(self.client, selectors.EVENT_READ)
        self.sel.register(self.server, selectors.EVENT_READ)
        self.sel.register(self.stop_evt, selectors.EVENT_READ)
        self.sel.register(self.client.change_size_evt, selectors.EVENT_READ)
        while not self.is_finished:
            events = self.sel.select(timeout=60)
            if self.client.closed:
                break
            if self.server.closed:
                break
            for sock in [key.fileobj for key, _ in events]:
                data = sock.recv(1024)
                if sock == self.server:
                    if len(data) == 0:
                        msg = "Server close the connection"
                        pretty_logger.info(msg)
                        self.is_finished = True
                        break

                    self.date_last_active = datetime.datetime.utcnow()
                    self.client.send(data)
                elif sock == self.client:
                    if len(data) == 0:
                        msg = "Client close the connection: {}".format(self.client)
                        pretty_logger.info(msg)
                        self.is_finished = True
                        break
                    self.server.send(data)
                elif sock == self.stop_evt:
                    self.is_finished = True
                    break
                elif sock == self.client.change_size_evt:
                    self.resize_win_size()
        pretty_logger.info("Session stop event set: {}".format(self.id))

    def resize_win_size(self):
        width, height = self.client.request.meta['width'], self.client.request.meta['height']
        #pretty_logger.info("Resize server chan size {}*{}".format(width, height))
        self.server.resize_pty(width=width, height=height)

    def close(self):
        if self.closed:
            pretty_logger.info("Session has been closed: {} ".format(self.id))
            return
        pretty_logger.info("Close the session: {} ".format(self.id))
        self.is_finished = True
        self.closed = True
        self.date_end = datetime.datetime.utcnow()

    def to_json(self):
        return {
            "id": self.id,
            "user": "{}".format(self.client.user.username),
            "asset": self.server.asset.ip,
            "system_user": self.server.system_user.username,
            "login_from": self.client.login_from,
            "remote_addr": self.client.addr[0],
            "is_finished": self.is_finished,
            "date_start": self.date_start.strftime("%Y-%m-%d %H:%M:%S") + " +0000",
            "date_end": self.date_end.strftime("%Y-%m-%d %H:%M:%S") + " +0000" if self.date_end else None
        }

    def __str__(self):
        return self.id

    def __repr__(self):
        return self.id
