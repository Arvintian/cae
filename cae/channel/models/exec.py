from cae.channel.utils import SelectEvent
from pretty_logging import pretty_logger
import uuid
import datetime
import selectors
import socket
from docker.models.containers import Container, ExecResult
import traceback


class ExecServer:
    def __init__(self, client, asset, system_user, container: Container):
        """
        asset:{
            origin:(ip,port)
        }
        system_user:{
            destination:(ip,port)
        }
        """
        self.client = client
        self.asset: dict = asset
        self.system_user: dict = system_user
        self.server = None
        self.connecting = True
        self.container = container
        self.exec_id = None

    def proxy(self):
        self.server = self.get_server_conn()

        if not self.server:
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
            try:
                self.server.send("exit\n".encode())
            except Exception as e:
                pretty_logger.error(traceback.format_exc())
            self.server.close()
            msg = 'Session end, total {} now'.format(
                len(Session.sessions),
            )
            pretty_logger.info(msg)

    def get_server_conn(self):
        sock = self.exec_run(user=self.system_user.get("username"))
        if not hasattr(sock, "send"):
            sock = sock._sock
        return Server(chan=sock, asset=self.asset, system_user=self.system_user, container=self.container, exec_id=self.exec_id)

    def exec_run(self, stdout=True, stderr=True, stdin=True, tty=True,
                 privileged=False, user='', detach=False, stream=False,
                 sock=True, environment=None, workdir=None, demux=False):
        for cmd in ["/bin/bash", "/bin/sh"]:
            try:
                resp = self.container.client.api.exec_create(
                    self.container.id, cmd, stdout=stdout, stderr=stderr, stdin=stdin, tty=tty,
                    privileged=privileged, user=user, environment=environment,
                    workdir=workdir,
                )

                exec_output = self.container.client.api.exec_start(
                    resp['Id'], detach=detach, tty=tty, stream=stream, socket=sock,
                    demux=demux
                )
                self.exec_id = resp['Id']
                # resize pty
                width, height = self.client.request.meta['width'], self.client.request.meta['height']
                self.container.client.api.exec_resize(self.exec_id, height=height, width=width)

                return exec_output
            except Exception as e:
                pretty_logger.error("exec run error {} {}".format(self.container.id, cmd))
        raise Exception("container no shell")


class Server(object):

    def __init__(self, chan, asset, system_user, container: Container, exec_id):
        self.id = str(uuid.uuid4())
        self.chan = chan
        self.asset: dict = asset
        self.system_user: dict = system_user
        self._closed = False
        self.container = container
        self.exec_id = exec_id

    def fileno(self):
        return self.chan.fileno()

    def send(self, b):
        try:
            return self.chan.send(b)
        except (OSError, EOFError, socket.error) as e:
            pretty_logger.error("Send to client {} error: {} {}".format(self, e, traceback.format_exc()))
            return 0

    def send_unicode(self, s):
        b = s.encode()
        self.send(b)

    @property
    def closed(self):
        return self._closed

    def recv(self, size):
        return self.chan.recv(size)

    def close(self):
        pretty_logger.info("Server {} close".format(self))
        if self.chan:
            self.chan.close()
        self._closed = True
        return

    def resize_pty(self, width, height):
        self.container.client.api.exec_resize(self.exec_id, height=height, width=width)

    def __getattr__(self, item):
        return getattr(self.chan, item)

    def __str__(self):
        return "server %s:%s" % (self.asset, self.system_user)


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
        # self.resize_win_size()
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
        # pretty_logger.info("Resize server chan size {}*{}".format(width, height))
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
            "asset": self.server.asset,
            "system_user": self.server.system_user,
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
