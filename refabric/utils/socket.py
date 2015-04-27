import warnings

try:
    from urlparse import urlsplit, urlunsplit
except ImportError:
    # Python 3
    from urllib.parse import urlsplit, urlunsplit

from enum import Enum


class Socket:
    """
    Representation of a socket. Contains the socket location and the socket
    type.

    Socket instances can be created with ``Socket(location, socket_type)`` or
    ``Socket.from_str(socket_string)`` where ``socket_string`` can be of any
    of the formats:

    - ``/path/to/unix/socket`` or ``any_ignored_scheme:///path/to/unix/socket``
    - ``127.0.0.1:1234`` or ``tcp://127.0.0.1:1234`` or ``udp://127.0.0.1:1234``
    """
    Protocols = Enum('SocketProtocols', 'INET UNIX')
    # TODO: add AF_UNIX types: DGRAM, STREAM?
    Types = Enum('SocketTypes', 'TCP UDP')
    type_map = {
        'tcp': Types.TCP,
        'udp': Types.UDP,
    }

    def __init__(self, location, protocol, socket_type=None):

        if not location:
            raise ValueError('Invalid location: {!r}'.format(location))

        if not protocol in self.Protocols:
            raise ValueError('Unknown protocol: {!r}'.format(protocol))

        if socket_type is not None and socket_type not in self.Types:
            raise ValueError('Unknown type: {!r}'.format(socket_type))

        self.location, self.protocol = location, protocol
        self.socket_type = socket_type

    def split_location(self):
        if self.type == self.Types.UNIX:
            warnings.warn('Unix sockets ({}) can not be split into host and '
                          'port'.format(self.location))
            return None, None

        host, _, port = self.location.partition(':')

        return host, port

    @property
    def port(self):
        return self.split_location()[1]

    @property
    def host(self):
        return self.split_location()[0]

    @classmethod
    def from_str(cls, string):
        parts = urlsplit(string)

        # Naked IP:PORT is mistaken for path
        if not parts.netloc and ':' in parts.path:
            parts = urlsplit('//{}'.format(string))

        tmpl_unrecognized = 'Unrecognised format: "{}" - {}'.format(string,
                                                                    '{}')

        if parts.netloc and parts.path:
            raise ValueError(tmpl_unrecognized.format('IP address with path'))

        if parts.netloc and not parts.port:
            raise ValueError(
                tmpl_unrecognized.format('IP address with no port'))

        if not parts.netloc and not parts.path:
            raise ValueError(tmpl_unrecognized.format('Neither IP nor path'))

        if not parts.netloc and parts.path:
            return cls(parts.path, cls.Protocols.UNIX)

        if parts.netloc and not parts.path:
            socket_type = cls.type_map.get(parts.scheme)
            return cls(parts.netloc, cls.Protocols.INET, socket_type)

    def get_type_name(self, default=None):
        return {v: k
                for k, v in self.type_map.items()}.get(self.socket_type,
                                                       default)

    def __repr__(self):
        return '<Socket type={} location={}{socket_type}>'.format(
            self.protocol,
            self.location,
            socket_type=' socket_type={}'.format(self.socket_type)
                        if self.socket_type is not None
                        else '')

    def __str__(self):
        if self.protocol == self.Protocols.UNIX:
            return urlunsplit(('unix', '', self.location, '', ''))

        if self.protocol == self.Protocols.INET:
            scheme = self.get_type_name()
            return urlunsplit(())


def format_socket(socket, template='{scheme}://{location}',
                  unix_template=None,
                  defaults=None):
    """
    Create a string representation of a socket according to ``template``. If
    unix and inet socket representations differ in format,
    use ``unix_template`` to specify the format for unix sockets.

    If the ``socket`` param isn't an instance of Socket it will be converted
    to the result of ``Socket.from_str(socket)``.

    The template is used with python's :py:function:`string.format()`. The
    template has two variables in context, ``scheme`` and ``location``.

    :param socket: socket instance or string.
    :param template: string.format() template, default: '{scheme}://{location}
    :param unix_template: optionally a template to use for unix sockets.
    :param defaults: default context variables
    :return: socket string

    Example:
    >>> format_socket('/var/run/gunicorn/app.sock')
    'unix:///var/run/gunicorn/app.sock'
    >>> from functools import partial
    >>> inet_socket = Socket.from_str('127.0.0.1:4321')
    >>> inet_udp_socket = Socket.from_str('udp://127.0.0.1:4321')
    >>> unix_socket = Socket.from_str('/var/run/gunicorn/app.sock')
    >>> nginx_fmt_socket = partial(format_socket,
    ...                            template='{scheme}://{location}',
    ...                            unix_template='unix:{location}',
    ...                            defaults={'scheme': 'tcp'})
    >>> nginx_fmt_socket(inet_socket)
    'tcp://127.0.0.1:4321'
    >>> nginx_fmt_socket(inet_udp_socket)
    'udp://127.0.0.1:4321'
    >>> nginx_fmt_socket(unix_socket)
    'unix:/var/run/gunicorn/app.sock'
    """
    if not isinstance(socket, Socket):
        socket = Socket.from_str(socket)

    if defaults is None:
        defaults = {}

    context = {
        'location': socket.location
    }

    if socket.protocol == Socket.Protocols.INET:
        context.update({
            'scheme': socket.get_type_name(default=defaults.get('scheme'))
        })
    elif socket.protocol == Socket.Protocols.UNIX:
        context.update({
            'scheme': defaults.get('unix_scheme', 'unix')
        })

    for k, v in defaults.items():
        context.setdefault(k, v)

    if unix_template is not None and socket.protocol == Socket.Protocols.UNIX:
        template = unix_template

    return template.format(**context)