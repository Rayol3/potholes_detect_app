import socket
import struct
import numpy as np
import cv2

class TCPFrameReceiver:
    def __init__(self, host='0.0.0.0', port=5005):
        self.host = host
        self.port = port
        self.server_socket = None
        self.conn = None
        self.running = False
        self.is_connected = False
        
        # Buffer for reading
        self.payload_size = struct.calcsize(">L")

    def open(self):
        """Starts the server and waits for a connection (Blocking in a way, but we will handle it)"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(1)
            self.server_socket.settimeout(1.0) # Non-blocking accept check
            self.running = True
            print(f"TCPFrameReceiver listening on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Error opening TCP server: {e}")
            return False

    def isOpened(self):
        return self.running

    def read(self):
        """
        Mimics cv2.VideoCapture.read()
        Returns: (ret, frame)
        """
        if not self.running:
            return False, None, None

        # Accept connection if not connected
        if not self.conn:
            try:
                self.conn, addr = self.server_socket.accept()
                self.conn.settimeout(1.0) # Ensure client reads also timeout so we can check running flag
                self.is_connected = True
                print(f"Connection from {addr}")
            except socket.timeout:
                return False, None, None # No connection yet
            except Exception as e:
                print(f"Accept error: {e}")
                return False, None, None

        # Read Frame
        try:
            # 1. Read Message Size
            data = b""
            while len(data) < self.payload_size:
                try:
                    packet = self.conn.recv(self.payload_size - len(data))
                except socket.timeout:
                    if len(data) == 0:
                        # Timeout waiting for NEW packet (Idle) -> Keep connection, just return
                        return False, None, None
                    else:
                        # Timeout IN THE MIDDLE of header -> Desync -> Close
                        print("Timeout receiving header")
                        self.close_client()
                        return False, None, None
                
                if not packet:
                    self.close_client()
                    return False, None, None
                data += packet
            
            packed_msg_size = data
            msg_size = struct.unpack(">L", packed_msg_size)[0]

            # 2. Read Frame Data
            data = b""
            while len(data) < msg_size:
                try:
                    packet = self.conn.recv(min(4096, msg_size - len(data)))
                except socket.timeout:
                    print("Timeout receiving payload")
                    self.close_client()
                    return False, None, None
                    
                if not packet: 
                    self.close_client()
                    return False, None, None
                data += packet
            
            # 3. Decode
            # Structure: [ImageLen(4)][ImageBytes][DepthLen(4)][DepthBytes]
            if len(data) < 4:
                return False, None, None
                
            offset = 0
            
            # Image Len
            img_len = struct.unpack(">L", data[offset:offset+4])[0]
            offset += 4
            
            if len(data) < offset + img_len:
                return False, None, None
                
            image_bytes = data[offset:offset+img_len]
            offset += img_len
            
            # Depth Len
            depth_data = None
            if len(data) >= offset + 4:
                 depth_len = struct.unpack(">L", data[offset:offset+4])[0]
                 offset += 4
                 if len(data) >= offset + depth_len:
                     depth_data = data[offset:offset+depth_len]

            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                return True, frame, depth_data
            else:
                return False, None, None
                
        except Exception as e:
            print(f"Receive error: {e}")
            self.close_client()
            return False, None, None

    def close_client(self):
        if self.conn:
            try:
                self.conn.close()
            except: 
                pass
            self.conn = None
            self.is_connected = False
            print("Client disconnected")

    def release(self):
        self.running = False
        self.close_client()
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
            self.server_socket = None
