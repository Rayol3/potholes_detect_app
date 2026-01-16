import struct

def recvall(sock, count):
    """
    Read exactly count bytes from the socket.
    Returns b'' if the connection is closed before reading count bytes.
    """
    buf = b''
    while len(buf) < count:
        newbuf = sock.recv(count - len(buf))
        if not newbuf:
            return b''
        buf += newbuf
    return buf

def read_uint32_be(sock):
    """Read a 4-byte unsigned integer (big-endian) from the socket."""
    data = recvall(sock, 4)
    if not data:
        return None
    return struct.unpack('>I', data)[0]
