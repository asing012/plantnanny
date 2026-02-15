import usocket

def post(url, data=None, headers={}):
    # 1. Parse the URL
    proto, dummy, host, path = url.split("/", 3)
    port = 80
    
    # 2. Open Connection
    addr = usocket.getaddrinfo(host, port)[0][-1]
    s = usocket.socket()
    s.connect(addr)
    
    # 3. Construct HTTP Request
    # Ensure payload is bytes and handle None
    if data is None:
        payload = b""
    elif isinstance(data, bytes):
        payload = data
    else:
        payload = data.encode('utf-8')
    request = b"POST /%s HTTP/1.0\r\n" % path
    request += b"Host: %s\r\n" % host
    request += b"Content-Length: %d\r\n" % len(payload)
    request += b"\r\n"
    request += payload
    
    # 4. Send & Close
    s.write(request)
    s.close()