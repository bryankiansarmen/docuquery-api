import socket, ssl
host = "ac-tipf1fj-shard-00-00.0nffocw.mongodb.net"
for proto in (ssl.PROTOCOL_TLS_CLIENT,):
    ctx = ssl.create_default_context()
    ctx.check_hostname = True
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    try:
        raw = socket.create_connection((host, 27017), timeout=8)
        with ctx.wrap_socket(raw, server_hostname=host) as s:
            print("Handshake OK:", s.version())
    except Exception as e:
        print("FAIL:", type(e).__name__, str(e)[:200])