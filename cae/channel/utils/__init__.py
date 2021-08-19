import os
from io import StringIO
import paramiko
from . import char
import re
import pyte
from binascii import hexlify
import socket


def ssh_key_string_to_obj(text, password=None):
    key = None
    try:
        key = paramiko.RSAKey.from_private_key(StringIO(text), password=password)
    except paramiko.SSHException:
        pass

    try:
        key = paramiko.DSSKey.from_private_key(StringIO(text), password=password)
    except paramiko.SSHException:
        pass
    return key


def ssh_pubkey_gen(private_key=None, username='jumpserver', hostname='localhost'):
    if isinstance(private_key, str):
        private_key = ssh_key_string_to_obj(private_key)

    if not isinstance(private_key, (paramiko.RSAKey, paramiko.DSSKey)):
        raise IOError('Invalid private key')

    public_key = "%(key_type)s %(key_content)s %(username)s@%(hostname)s" % {
        'key_type': private_key.get_name(),
        'key_content': private_key.get_base64(),
        'username': username,
        'hostname': hostname,
    }
    return public_key


def ssh_key_gen(length=2048, type='rsa', password=None,
                username='cae', hostname=None):
    """Generate user ssh private and public key

    Use paramiko RSAKey generate it.
    :return private key str and public key str
    """

    if hostname is None:
        hostname = os.uname()[1]

    f = StringIO()

    if type == 'rsa':
        private_key_obj = paramiko.RSAKey.generate(length)
    elif type == 'dsa':
        private_key_obj = paramiko.DSSKey.generate(length)
    else:
        raise IOError('SSH private key must be `rsa` or `dsa`')

    private_key_obj.write_private_key(f, password=password)
    private_key = f.getvalue()
    public_key = ssh_pubkey_gen(private_key_obj, username=username, hostname=hostname)

    return private_key, public_key


class TtyIOParser(object):
    def __init__(self, width=80, height=24):
        self.screen = pyte.Screen(width, height)
        self.stream = pyte.ByteStream()
        self.stream.attach(self.screen)
        self.ps1_pattern = re.compile(r'^\[?.*@.*\]?[\$#]\s|mysql>\s')

    def clean_ps1_etc(self, command):
        return self.ps1_pattern.sub('', command)

    def parse_output(self, data, sep='\n'):
        """
        Parse user command output

        :param data: output data list like, [b'data', b'data']
        :param sep:  line separator
        :return: output unicode data
        """
        output = []

        for d in data:
            self.stream.feed(d)
        try:
            for line in self.screen.display:
                if line.strip():
                    output.append(line)
        except IndexError:
            pass
        self.screen.reset()
        return sep.join(output[0:-1]).strip()

    def parse_input(self, data):
        """
        Parse user input command

        :param data: input data list, like [b'data', b'data']
        :return: command unicode
        """
        command = []
        for d in data:
            self.stream.feed(d)
        for line in self.screen.display:
            line = line.strip()
            if line:
                command.append(line)
        if command:
            command = command[-1]
        else:
            command = ''
        self.screen.reset()
        command = self.clean_ps1_etc(command)
        return command.strip()


def wrap_with_line_feed(s, before=0, after=1):
    if isinstance(s, bytes):
        return b'\r\n' * before + s + b'\r\n' * after
    return '\r\n' * before + s + '\r\n' * after


def wrap_with_color(text, color='white', background=None,
                    bolder=False, underline=False):
    bolder_ = '1'
    _underline = '4'
    color_map = {
        'black': '30',
        'red': '31',
        'green': '32',
        'brown': '33',
        'blue': '34',
        'purple': '35',
        'cyan': '36',
        'white': '37',
    }
    background_map = {
        'black': '40',
        'red': '41',
        'green': '42',
        'brown': '43',
        'blue': '44',
        'purple': '45',
        'cyan': '46',
        'white': '47',
    }

    wrap_with = []
    if bolder:
        wrap_with.append(bolder_)
    if underline:
        wrap_with.append(_underline)
    if background:
        wrap_with.append(background_map.get(background, ''))
    wrap_with.append(color_map.get(color, ''))

    is_bytes = True if isinstance(text, bytes) else False

    if is_bytes:
        text = text.decode("utf-8")
    data = '\033[' + ';'.join(wrap_with) + 'm' + text + '\033[0m'
    if is_bytes:
        return data.encode('utf-8')
    else:
        return data


def wrap_with_warning(text, bolder=False):
    return wrap_with_color(text, color='red', bolder=bolder)


def wrap_with_info(text, bolder=False):
    return wrap_with_color(text, color='brown', bolder=bolder)


def wrap_with_primary(text, bolder=False):
    return wrap_with_color(text, color='green', bolder=bolder)


def wrap_with_title(text):
    return wrap_with_color(text, color='black', background='green')


def net_input(client, prompt='Opt> ', sensitive=False, before=0, after=0):
    """实现了一个ssh input, 提示用户输入, 获取并返回

    :return user input string
    """
    input_data = []
    parser = TtyIOParser()
    msg = wrap_with_line_feed(prompt, before=before, after=after)
    client.send_unicode(msg)

    while True:
        data = client.recv(1)
        if len(data) == 0 or client.closed:
            break
        # Client input backspace
        if data in char.BACKSPACE_CHAR:
            # If input words less than 0, should send 'BELL'
            if len(input_data) > 0:
                data = char.BACKSPACE_CHAR[data]
                input_data.pop()
            else:
                data = char.BELL_CHAR
            client.send(data)
            continue

        if data.startswith(b'\x03'):
            # Ctrl-C
            client.send_unicode('^C\r\n{} '.format(prompt))
            input_data = []
            continue
        elif data.startswith(b'\x04'):
            # Ctrl-D
            return 'q'

        # Todo: Move x1b to char
        if data.startswith(b'\x1b') or data in char.UNSUPPORTED_CHAR:
            client.send(b'')
            continue

        # If user types ENTER we should get user input
        if data in char.ENTER_CHAR:
            client.send(wrap_with_line_feed(b'', after=2))
            option = parser.parse_input(input_data)
            del input_data[:]
            return option.strip()
        else:
            if sensitive:
                client.send_unicode((len(data) * '*'))
            else:
                client.send(data)
            input_data.append(data)


def get_private_key_fingerprint(key):
    line = hexlify(key.get_fingerprint())
    return b':'.join([line[i:i+2] for i in range(0, len(line), 2)])


class ObjDict(dict):
    """
    Makes a  dictionary behave like an object,with attribute-style access.
    """
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class SelectEvent:
    def __init__(self):
        self.p1, self.p2 = socket.socketpair()

    def set(self):
        self.p2.send(b'0')

    def fileno(self):
        return self.p1.fileno()

    def __getattr__(self, item):
        return getattr(self.p1, item)


def parser_public_key(public_key: str):
    s = public_key.split(" ")
    if len(s) == 1:
        return s
    elif len(s) == 2:
        return s[-1]
    elif len(s) >= 3:
        return s[1]
