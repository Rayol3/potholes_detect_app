import socket
import threading
from .protocol import recvall, read_uint32_be
from .. import config

class TCPServer:
    def __init__(self, host=config.HOST, port=config.PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False

    def start(self, handler_callback):
        """
        Starts the TCP Server.
        handler_callback: Function that accepts (data_bytes)
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True
        
        print(f"Server listening on {self.host}:{self.port}")
        
        try:
            while self.running:
                conn, addr = self.socket.accept()
                print(f"Connected to {addr}")
                self._handle_client(conn, handler_callback)
        except KeyboardInterrupt:
            self.stop()
        finally:
            self.stop()

    def _handle_client(self, conn, handler_callback):
        with conn:
            while True:
                # 1. Read Payload Size (4 bytes)
                payload_size = read_uint32_be(conn)
                if payload_size is None:
                    print("Client disconnected.")
                    break
                
                # 2. Read Payload
                data = recvall(conn, payload_size)
                if len(data) < payload_size:
                    print("Incomplete packet received.")
                    break
                
                # 3. Process Data
                handler_callback(data)

    def stop(self):
        self.running = False
        if self.socket:
            self.socket.close()
            print("Server stopped.")
