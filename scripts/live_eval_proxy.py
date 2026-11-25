"""Allowlist HTTPS proxy for isolated live evals.

The eval user's traffic may reach only this proxy (iptables, set up by the workflow), and the
proxy tunnels only CONNECT requests to allowlisted host:port pairs. Claude Code honours
HTTPS_PROXY, so model calls reach the API while anything the agent under test runs cannot
reach other hosts.
"""
import argparse
import select
import socket
import socketserver
import sys


class Proxy(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, allow, log=sys.stderr):
        self.allow = {a.lower() for a in allow}
        self.log = log
        super().__init__(address, Handler)


class Handler(socketserver.StreamRequestHandler):
    def reply(self, status):
        self.wfile.write(f'HTTP/1.1 {status}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n'.encode())

    def handle(self):
        line = self.rfile.readline(8192).decode('latin-1').strip()
        while self.rfile.readline(8192) not in (b'\r\n', b'\n', b''):
            pass
        parts = line.split()
        if len(parts) != 3 or parts[0].upper() != 'CONNECT':
            print(f'live-eval proxy: refused non-CONNECT request', file=self.server.log, flush=True)
            return self.reply('405 Method Not Allowed')
        target = parts[1].lower()
        if target not in self.server.allow:
            print(f'live-eval proxy: refused {target}', file=self.server.log, flush=True)
            return self.reply('403 Forbidden')
        host, _, port = target.rpartition(':')
        try:
            upstream = socket.create_connection((host, int(port)), timeout=30)
        except OSError:
            return self.reply('502 Bad Gateway')
        self.reply('200 Connection Established')
        self.wfile.flush()
        sockets = [self.connection, upstream]
        try:
            while True:
                ready, _, broken = select.select(sockets, [], sockets, 300)
                if broken or not ready:
                    break
                for sock in ready:
                    data = sock.recv(65536)
                    if not data:
                        return
                    (upstream if sock is self.connection else self.connection).sendall(data)
        finally:
            upstream.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--listen', default='127.0.0.1:3128')
    parser.add_argument('--allow', action='append', required=True, help='host:port to tunnel (repeatable)')
    args = parser.parse_args(argv)
    host, _, port = args.listen.rpartition(':')
    with Proxy((host, int(port)), args.allow) as server:
        print(f'live-eval proxy listening on {args.listen}, allowing {", ".join(sorted(server.allow))}', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
