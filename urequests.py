import usocket

def post(url, data=None, headers={}):
    url = url.replace("http://", "")
    if "/" in url:
        host_port, path = url.split("/", 1)
    else:
        host_port, path = url, ""

    if ":" in host_port:
        host, port = host_port.split(":")
        port = int(port)
    else:
        host, port = host_port, 80

    if isinstance(data, str):
        payload = data.encode('utf-8')
    elif isinstance(data, bytes):
        payload = data
    else:
        payload = b""

    s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    s.connect((host, port))

    request  = f"POST /{path} HTTP/1.0\r\n".encode()
    request += f"Host: {host}\r\n".encode()
    request += f"Content-Length: {len(payload)}\r\n".encode()
    for k, v in headers.items():
        request += f"{k}: {v}\r\n".encode()
    request += b"\r\n"
    request += payload

    s.write(request)
    response = s.read(128)
    s.close()
    return response