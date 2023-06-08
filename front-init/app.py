import pathlib
import urllib.parse
import mimetypes
import json
import logging
import socket

from pathlib import Path
from threading import RLock, Thread
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(filename='app.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
storage_path = Path("storage")
storage_path.mkdir(parents=True, exist_ok=True)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_address = ("", 5000)
server_socket.bind(server_address)

lock = RLock()


def save_data(data_dict):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    data = {current_time: data_dict}

    file_path = storage_path / "data.json"
    with lock:
        if file_path.exists():
            with open(file_path, "r") as file:
                try:
                    existing_data = json.load(file)
                    # existing_data.append("\n")
                    print(existing_data)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []

        existing_data.append(data)
        print(existing_data)

        with open(file_path, "w") as file:
            json.dump(existing_data, file, indent=4)

    logging.info("Message saved successfully!")


class HTTPHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case "/":
                self.send_html('index.html')
            case "/message":
                self.send_html('message.html')
            case _:
                file = Path().joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Tpe', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def send_static(self, filename):
        self.send_response(200)
        mime_type, *rest = mimetypes.guess_type(filename)
        if mime_type:
            self.send_header('Content-Type', mime_type)
        else:
            self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as f:
            self.wfile.write(f.read())

    def _set_response(self):
        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def do_POST(self):
        data = self.rfile.read(int(self.headers['Content-Length']))
        print(data)
        data_parse = urllib.parse.unquote_plus(data.decode())
        print(data_parse)
        data_dict = {key: value for key, value in [el.split('=') for el in data_parse.split('&')]}
        try:
            send_message_socket(json.dumps(data_dict))
            self._set_response()
            self.wfile.write(b"Message received and saved successfully!")
        except json.JSONDecodeError:
            self._set_response()
            self.wfile.write(b"Error: Invalid data format.")


def run(server=HTTPServer, handler=HTTPHandler):
    address = ('0.0.0.0', 3000)
    http_server = server(address, handler)
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        http_server.server_close()


def send_message_socket(data):
    server_socket.sendto(data.encode(), ("localhost", 5000))


def run_socket_server():
    while True:
        data, address = server_socket.recvfrom(4096)
        try:
            data_dict = json.loads(data.decode())
        except json.JSONDecodeError:
            print("Error: Incorrect type of data.")
            continue

        save_data(data_dict)

        print("Data save in file data.json.")


if __name__ == '__main__':
    http_thread = Thread(target=run)
    http_thread.start()

    socket_thread = Thread(target=run_socket_server)
    socket_thread.start()
