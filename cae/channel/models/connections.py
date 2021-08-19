import socket
import uuid
from pretty_logging import pretty_logger
from cae.channel.utils import ObjDict, SelectEvent


class Connection(object):
    connections = {}
    clients_num = 0

    def __init__(self, cid=None, sock=None, addr=None):
        if not cid:
            cid = str(uuid.uuid4())
        self.id = cid
        self.sock = sock
        self.addr = addr
        self.user = None
        self.otp_auth = False
        self.login_from = 'ST'
        self.clients = {}

    def __str__(self):
        return '<{} from {}>'.format(self.user, self.addr)

    def new_client(self, tid, chan=None):
        client = Client(
            tid=tid, user=self.user, addr=self.addr,
            login_from=self.login_from
        )
        client.connection_id = self.id
        self.clients[tid] = client
        self.__class__.clients_num += 1
        pretty_logger.info("New client {} join, total {} now".format(
            client, self.__class__.clients_num
        ))
        return client

    def get_client(self, tid):
        if hasattr(tid, 'get_id'):
            tid = tid.get_id()
        client = self.clients.get(tid)
        return client

    def remove_client(self, tid):
        client = self.get_client(tid)
        if not client:
            return
        client.close()
        self.__class__.clients_num -= 1
        self.clients.pop(tid, None)
        pretty_logger.info("Client {} leave, total {} now".format(
            client, self.__class__.clients_num
        ))

    def close(self):
        clients_copy = self.clients.keys()
        for tid in clients_copy:
            self.remove_client(tid)
        self.sock.close()

    @classmethod
    def new_connection(cls, addr, sock=None, cid=None):
        if not cid:
            cid = str(uuid.uuid4())
        connection = cls(cid=cid, sock=sock, addr=addr)
        cls.connections[cid] = connection
        return connection

    @classmethod
    def remove_connection(cls, cid):
        connection = cls.get_connection(cid)
        if not connection:
            return
        connection.close()
        cls.connections.pop(cid, None)

    @classmethod
    def get_connection(cls, cid):
        return cls.connections.get(cid)


class Request(object):
    def __init__(self):
        self.type = None
        self.x11 = None
        self.kind = None
        self.meta = {'env': {}}


class Client(object):
    """
    Client is the request client. Nothing more to say

    ```
    client = Client(chan, addr, user)
    ```
    """

    def __init__(self, tid=None, user=None, addr=None, login_from=None, chan=None):
        if tid is None:
            tid = str(uuid.uuid4())
        self.id = tid
        self.user = ObjDict()
        if user:
            self.user.update(user)
        self.addr = addr
        self.chan = chan
        self.request = Request()
        self.connection_id = None
        self.login_from = login_from
        self.change_size_evt = SelectEvent()

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
        pretty_logger.info("Client {} close".format(self))
        if self.chan:
            self.chan.close()
        return

    def __getattr__(self, item):
        return getattr(self.chan, item)

    def __str__(self):
        return "user:%s instance:%s from %s:%s" % (self.user.get("username"), self.user.get("instance_id"), self.addr[0], self.addr[1])
