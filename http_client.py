import socket
import sys
import os
import re
from urllib.parse import urljoin, urlsplit

# חיבור לשרת
def connect_to_server(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    return client_socket

# בניית בקשת GET
def build_request(host, path):
    request = (
        f"GET {path} HTTP/1.0\r\n"
        f"Host: {host}\r\n"
        f"\r\n"
    )

    return request.encode("ascii")

# שולח את הבקשה לשרת
def send_request(client_socket, request):
    client_socket.sendall(request)

# קורא את כותרות התגובה מהשרת
def read_headers(client_socket):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = client_socket.recv(4096)
        if not chunk:
            break
        data += chunk

    if b"\r\n\r\n" not in data:
        return None, None

    header_data, body_start = data.split(b"\r\n\r\n", 1)

    return header_data, body_start

# מפרק את כותרות ה-HTTP שקיבלנו
def parse_response_headers(header_data):
    try:
        text = header_data.decode("iso-8859-1")
        lines = text.split("\r\n")

        status_line = lines[0]
        parts = status_line.split(" ", 2)

        version = parts[0]
        status_code = int(parts[1])
        reason = parts[2] if len(parts) > 2 else ""

    except (ValueError, IndexError):
        return None

    headers = {}

    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()

    return version, status_code, reason, headers

# קריאת ה-body
def read_body(client_socket, body_start, content_length):
    body = body_start
    while len(body) < content_length:
        chunk = client_socket.recv(
            min(4096, content_length - len(body))
        )

        if not chunk:
            break

        body += chunk

    if len(body) != content_length:
        return None

    return body

# מבצע בקשה מלאה למשאב מהשרת
def fetch_resource(host, port, path):
    client_socket = None

    try:
        client_socket = connect_to_server(host, port)

        request = build_request(host, path)
        send_request(client_socket, request)

        header_data, body_start = read_headers(client_socket)

        if header_data is None:
            print("Invalid HTTP response")
            return None

        parsed = parse_response_headers(header_data)

        if parsed is None:
            print("Could not parse HTTP response")
            return None

        version, status_code, reason, headers = parsed

        content_length = 0

        if "content-length" in headers:
            try:
                content_length = int(headers["content-length"])
            except ValueError:
                print("Invalid Content-Length")
                return None

        body = read_body(
            client_socket,
            body_start,
            content_length
        )

        if body is None:
            print("Incomplete response body")
            return None

        return status_code, reason, headers, body

    except OSError as error:
        print("Connection error:", error)
        return None

    finally:
        if client_socket is not None:
            client_socket.close()


# שומר את הקובץ שהתקבל בתיקיית output
def save_resource(path, body):
    clean_path = path.split("?", 1)[0]
    clean_path = clean_path.lstrip("/")

    if not clean_path:
        clean_path = "index.html"
    output_path = os.path.join("output", clean_path)

    output_directory = os.path.dirname(output_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)

    with open(output_path, "wb") as file:
        file.write(body)

    print("Saved:", output_path)

# בודק את הנתיב של משאב מתוך ה-HTML
def get_resource_path(resource, host, port, base_path):
    if port == 80:
        base_url = f"http://{host}{base_path}"
    else:
        base_url = f"http://{host}:{port}{base_path}"

    resolved_url = urljoin(base_url, resource)
    parsed_url = urlsplit(resolved_url)

    if parsed_url.scheme != "http":
        return None

    resource_host = parsed_url.hostname
    resource_port = parsed_url.port if parsed_url.port is not None else 80

    if resource_host is None:
        return None

    if resource_host.lower() != host.lower() or resource_port != port:
        return None

    resource_path = parsed_url.path or "/"

    if parsed_url.query:
        resource_path += "?" + parsed_url.query

    return resource_path

# מחפש תמונות וקבצי CSS בתוך ה-HTML
def find_embedded_resources(html_body):
    try:
        html = html_body.decode("utf-8")
    except UnicodeDecodeError:
        return []
    img_sources = re.findall(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE
    )
    link_sources = re.findall(
        r'<link[^>]+href=["\']([^"\']+)["\']',
        html,
        re.IGNORECASE
    )

    return img_sources + link_sources

if __name__ == "__main__":
    host = "localhost"
    port = 8000
    path = "/index.html"

    if len(sys.argv) > 1:
        host = sys.argv[1]

    if len(sys.argv) > 2:
        port = int(sys.argv[2])

    if len(sys.argv) > 3:
        path = sys.argv[3]

    print("Host:", host)
    print("Port:", port)
    print("Path:", path)

    result = fetch_resource(host, port, path)

    if result is not None:
        status_code, reason, headers, body = result

        if status_code == 200:
            print("200 OK")
            save_resource(path, body)

            resources = find_embedded_resources(body)

            for resource in resources:
                resource_path = get_resource_path(
                    resource,
                    host,
                    port,
                    path
                )

                if resource_path is None:
                    print("Skipping external resource:", resource)
                    continue

                print("Fetching embedded resource:", resource_path)

                resource_result = fetch_resource(
                    host,
                    port,
                    resource_path
                )

                if resource_result is None:
                    continue

                code, reason, resource_headers, resource_body = resource_result

                if code == 200:
                    save_resource(
                        resource_path,
                        resource_body
                    )

                elif code in (301, 302):
                    location = resource_headers.get("location", "")
                    print(f"Redirect {code}: {location}")

                else:
                    print(
                        f"Could not fetch {resource}: "
                        f"{code} {reason}"
                    )
        elif status_code in (301, 302):
            location = headers.get("location", "")
            print(f"Redirect {status_code}: {location}")

        else:
            print(f"HTTP error: {status_code} {reason}")