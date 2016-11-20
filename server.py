#! /bin/python3

import socket
import hashlib
import base64
from pipeline import PipeLine
from websocket_dataframe import DataFrame
from helpers import coroutine


PORT = 8999
HOST = "localhost"


class Server(object):
    
    def __init__(self):
        self.pipeline = PipeLine

    @coroutine
    def start_server(self):
        server_socket = socket.socket()
        server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1)
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        server_socket.setblocking(0)
        while True:
            try:
                in_sock, host = yield from self.yield_socket(server_socket, 'accept')
                in_sock.setblocking(0)
                self.pipeline.add_job(self.handle_incoming_connection(in_sock, host))
            except KeyboardInterrupt:
                server_socket.close()
                break

    def yield_socket(self, socket, func_name, *args, **kwargs):
        call = getattr(socket, func_name)
        while True:
            try:
                result =  call(*args, **kwargs)
                return result
            except BlockingIOError:
                yield

    def handle_incoming_connection(self, in_sock, host):
        data = yield from self.yield_socket(in_sock, 'recv', 4);
        in_sock.send(b'pong\r\n')
        in_sock.close()
        return 

    def run(self):
        server_ = self.start_server()
        execute_jobs = self.pipeline.execute()
        while True:
            next(server_)
            next(execute_jobs)


class AsyncWebSocketServer(Server):

    magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    response = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Accept: %s\r\n\r\n"
    
    @classmethod
    def get_value(cls, key):
        a = key + cls.magic_string
        hash_ = hashlib.sha1(a.encode("utf8"))
        return base64.b64encode(hash_.digest())

    @staticmethod
    def process_raw_body(body):
        return body.decode("unicode_escape")


    @staticmethod
    def process_raw_header(raw_header):
        status_and_headers = raw_header.split(b"\r\n")[:-2]
        status = status_and_headers[0]
        headers_list = status_and_headers[1:]
        headers = {}
        for header_text in headers_list:
            index = header_text.find(b":")
            header_key = header_text[:index].strip().decode("unicode_escape")
            header_value = header_text[index + 1: ].strip().decode("unicode_escape")
            headers[header_key] = header_value
        return status, headers

    def process_data(self, in_sock, host):
        raw_header = b""
        raw_body = b""
        while True:
            temp_data = yield from self.yield_socket(in_sock, 'recv', 1024)
            raw_header = raw_header + temp_data
            if raw_header.find(b"\r\n\r\n") > 0:
                header_end = raw_header.find(b"\r\n\r\n")
                raw_body = raw_body + raw_header[header_end + 4:]
                raw_header = raw_header[:header_end + 4]
                break
        status, headers = self.process_raw_header(raw_header)
        if headers.get("Content-Length"):
            content_length = int(headers.get("Content-Length")) - len(raw_body)
            temp_data = yield from self.yield_socket(in_sock, 'recv', 
                                                     content_length)
            raw_body = raw_body + temp_data
        body = self.process_raw_body(raw_body)
        return status, headers, body

    def handle_socket_handshake(self, in_sock, host):
        status, headers, body = yield from self.process_data(in_sock, host)
        key = headers.get("Sec-WebSocket-Key")
        send_key = self.get_value(key)
        response_ = self.response %(send_key)
        while True:
            try:
                in_sock.send(response_)
                return 
            except Exception as e:
                yield 

    def socket_view(self, recieved_data, close):
        return DataFrame(payload=recieved_data, close=close).raw_data

    def process_socket_request(self, in_sock, host):
        while True:
            fin = False 
            close = False
            recieved_data = ""

            while not fin:
                data = yield from self.yield_socket(in_sock, 'recv', 4096)
                try:
                    websocket_frame = DataFrame(data=data)
                except NotImplementedError:
                    in_sock.close()
                    return
                parsed_data = websocket_frame.payload
                fin = websocket_frame.fin
                close = websocket_frame.close
                recieved_data = recieved_data + parsed_data

            raw_data = self.socket_view(recieved_data, close)
            in_sock.send(raw_data)
            if close:
                in_sock.close()
                return

    def handle_incoming_connection(self, in_sock, host):
        yield from self.handle_socket_handshake(in_sock, host)
        yield from self.process_socket_request(in_sock, host)
        return



if __name__ == '__main__':
    server = AsyncWebSocketServer()
    server.run()
