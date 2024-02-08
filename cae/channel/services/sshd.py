import os
import socket
from cae.config import channel_config as config
from cae.channel.utils import ssh_key_gen
from cae.channel.models import Connection, SSHInterface, InteractiveServer
from pretty_logging import pretty_logger
import threading
import traceback
import paramiko


class SSHServer:
    def __init__(self):
        self.stop_evt = threading.Event()

    @property
    def host_key(self):
        host_key_path = config["HOST_PRIVATE_KEY"]
        if not os.path.isfile(host_key_path):
            self.gen_host_key()
        return paramiko.RSAKey(filename=host_key_path)

    @staticmethod
    def gen_host_key():
        ssh_private_key, ssh_public_key = ssh_key_gen()
        with open(config["HOST_PRIVATE_KEY"], 'w', encoding="utf-8") as f:
            f.write(ssh_private_key)
        with open(config["HOST_PUBLIC_KEY"], "w", encoding="utf-8") as f:
            f.write(ssh_public_key)

    def run(self):
        host = config["BIND_HOST"]
        port = config["SSHD_PORT"]
        pretty_logger.info("Starting ssh server at {}:{}".format(host, port))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        sock.bind((host, port))
        sock.listen(os.cpu_count())
        while not self.stop_evt.is_set():
            try:
                client, addr = sock.accept()
                t = threading.Thread(target=self.handle_connection, args=(client, addr))
                t.daemon = True
                t.start()
            except Exception as e:
                pretty_logger.error(traceback.format_exc())
                pretty_logger.error("Start SSH server error: {}".format(e))

    def handle_connection(self, sock, addr):
        pretty_logger.info("Handle new connection from: {}".format(addr))
        transport = paramiko.Transport(sock, gss_kex=False)
        try:
            transport.load_server_moduli()
        except IOError:
            pretty_logger.warning("Failed load moduli -- gex will be unsupported")
        transport.add_server_key(self.host_key)
        connection = Connection.new_connection(addr=addr, sock=sock)
        server = SSHInterface(connection)
        try:
            transport.start_server(server=server)
            transport.set_keepalive(60)
            while transport.is_active():
                chan = transport.accept()
                server.event.wait(5)
                if chan is None:
                    continue

                if not server.event.is_set():
                    pretty_logger.warning("Client not request invalid, exiting")
                    sock.close()
                    continue
                else:
                    server.event.clear()

                client = connection.clients.get(chan.get_id())
                client.chan = chan
                t = threading.Thread(target=self.dispatch, args=(client,))
                t.daemon = True
                t.start()
            transport.close()
        except paramiko.SSHException as e:
            pretty_logger.debug("SSH negotiation failed: {}".format(e))
        except EOFError as e:
            pretty_logger.debug("Handle connection EOF Error: {}".format(e))
        except Exception as e:
            pretty_logger.error("Unexpect error occur on handle connection: {}".format(e))
        finally:
            Connection.remove_connection(connection.id)
            sock.close()

    @staticmethod
    def dispatch(client):
        supported = {"pty", "x11", "forward-agent", "direct-tcpip"}
        chan_type = client.request.type
        kind = client.request.kind
        try:
            pretty_logger.info("dispatch {} {}".format(kind, chan_type))
            if kind in ["session", "direct-tcpip"] and chan_type in supported:
                pretty_logger.info("Dispatch client to interactive {} mode".format(kind))
                try:
                    InteractiveServer(client).interact(kind)
                except IndexError as e:
                    pretty_logger.error("Unexpected error occur: {}".format(e))
            else:
                msg = "Request type `{}:{}` not support now".format(kind, chan_type)
                pretty_logger.error(msg)
                client.send_unicode(msg)
        finally:
            connection = Connection.get_connection(client.connection_id)
            if connection:
                connection.remove_client(client.id)

    def shutdown(self):
        self.stop_evt.set()
