import socket
import threading

class TCPServer:
    def __init__(self, host="0.0.0.0", port=8811, stream_callback=None):
        self.host = host
        self.port = port
        self.running = False
        self.sever_th = None
        self.stream_callback = stream_callback

    def start(self):
        self.running = True
        self.server_th = threading.Thread(target=self._serve_forever)
        self.server_th.start()

    def stop(self):
        print("Stopping TCP Server")
        self.running = False

    def _serve_forever(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((self.host, self.port))
            sock.listen()
            sock.settimeout(1)

            print("TCP Server started. Listening for client connections")

            while self.running:
                try:
                    conn, addr = sock.accept()
                    print(f"Client connected: {addr}")
                    stream = conn.makefile("wb")
                    # Notify main application about new stream
                    if self.stream_callback:
                        self.stream_callback(stream)
                except socket.timeout:
                    pass