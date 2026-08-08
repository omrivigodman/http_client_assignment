import socket
import os
import mimetypes
import threading
from urllib.parse import unquote

HOST = "127.0.0.1"
PORT = 8000
STATIC_ROOT = "static"
ALLOWED_DIRECTORIES = {"", "css", "pages", "js", "images"}

# פונקציה שקוראת את הבקשה מהלקוח
# כרגע אנחנו קוראים עד סוף כותרות \r\n\r\n
def read_http_request(connection):
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = connection.recv(1024)

        if not chunk:
            break
        data += chunk
    return data

# פונקציה שמפרקת את בקשת ה-HTTP
# היא מוציאה מהשורה הראשונה את method, path, version
def parse_http_request(request_data):
    request_text = request_data.decode("utf-8", errors="replace")
    lines = request_text.split("\r\n")
    request_line = lines[0]
    parts = request_line.split()

    if len(parts) != 3:
        return None, None, None

    method = parts[0]
    path = parts[1]
    version = parts[2]

    return method, path, version

# פונקציה שבונה תגובת HTTP כללית
def build_response(status_code, reason_phrase, body, content_type="text/html; charset=utf-8"):
    headers = [
        f"HTTP/1.0 {status_code} {reason_phrase}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body)}",
        "Connection: close",
        "",
        ""
    ]

    header_bytes = "\r\n".join(headers).encode("utf-8")

    return header_bytes + body

# פונקציה שבונה דף שגיאה
def build_error_response(status_code, reason_phrase, message):
    body = f"""
    <html>
        <head>
            <title>{status_code} {reason_phrase}</title>
        </head>
        <body>
            <h1>{status_code} {reason_phrase}</h1>
            <p>{message}</p>
        </body>
    </html>
    """.encode("utf-8")

    return build_response(status_code, reason_phrase, body)

# פונקציה שמחזירה את סוג הקובץ לפי הסיומת שלו
def get_content_type(file_path):
    content_type, _ = mimetypes.guess_type(file_path)

    if content_type is None:
        return "application/octet-stream"

    return content_type

# פונקציה שבודקת אם הנתיב נמצא בתיקייה שמותר לגשת אליה
def is_allowed_directory(path):
    # להוריד את הסימן מההתחלה
    clean_path = path.lstrip("/")

    if "/" not in clean_path:
        first_directory = ""
    else:
        # לוקחים את התיקייה הראשונה בנתיב
        first_directory = clean_path.split("/", 1)[0]

    return first_directory in ALLOWED_DIRECTORIES

# פונקציה שמחזירה קובץ אמיתי מתוך התיקייה הסטטית
def build_static_file_response(path):
    # אם יש שאילתה מורידים
    path = path.split("?", 1)[0]

    # מפענחים תווים מיוחדים בקישור
    path = unquote(path)

    if path == "/":
        path = "/index.html"

    # חסימה בסיסית של directory traversal
    if ".." in path:
        return build_error_response(
            403,
            "Forbidden",
            "Directory traversal is not allowed"
        )

    # בדיקה שהמשתמש ניגש רק לתיקיות שמותרות
    if not is_allowed_directory(path):
        return build_error_response(
            403,
            "Forbidden",
            "Access to this directory is not allowed."
        )

    # הופכים את הנתיב מהקישור לנתיב במחשב
    relative_path = path.lstrip("/")
    file_path = os.path.join(STATIC_ROOT, relative_path)

    # בדיקת אבטחה שהקובץ באמת בתוך התיקייה הסטטית
    static_root_abs = os.path.abspath(STATIC_ROOT)
    file_path_abs = os.path.abspath(file_path)

    if not file_path_abs.startswith(static_root_abs + os.sep):
        return build_error_response(
            403,
            "Forbidden",
            "Access outside the static directory is not allowed."
        )

    # אם הקובץ לא קיים אז נחזיר 404
    if not os.path.isfile(file_path_abs):
        return build_error_response(
            404,
            "Not Found",
            f"The requested file {path} was not found."
        )

    # אם הקובץ קיים אז נקרא אותו כבייט
    with open(file_path_abs, "rb") as file:
        body = file.read()

    content_type = get_content_type(file_path_abs)

    return build_response(200, "OK", body, content_type)

# פונקציה שמטפלת בלקוח אחד
def handle_client(connection, address):
    try:
        print(f"New connection from {address}")

        request = read_http_request(connection)

        print("------ HTTP REQUEST ------")
        print(request.decode("utf-8", errors="replace"))
        print("--------------------------")

        method, path, version = parse_http_request(request)

        print("------ PARSED REQUEST ------")
        print(f"Method: {method}")
        print(f"Path: {path}")
        print(f"Version: {version}")
        print("----------------------------")

        if method is None or path is None or version is None:
            response = build_error_response(
                400,
                "Bad Request",
                "The HTTP request line is invalid"
            )

        elif method != "GET":
            response = build_error_response(
                405,
                "Method Not Allowed",
                "Only GET requests are supported"
            )

        elif path == "/redirect":
            response = (
                "HTTP/1.0 302 Found\r\n"
                "Location: /index.html\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode("ascii")

        elif path == "/malformed":
            response = b"THIS IS NOT A VALID HTTP RESPONSE\r\n\r\n"

        else:
            response = build_static_file_response(path)

        connection.sendall(response)

    except Exception as error:
        print(f"Error while handling client {address}: {error}")

        try:
            response = build_error_response(
                500,
                "Internal Server Error",
                "The server encountered an unexpected error."
            )
            connection.sendall(response)
        except:
            pass

    finally:
        connection.close()


# הפונקציה יוצרת שרת TCP ומקבלת לקוחות בלולאה
def start_server():

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    print(f"Server is running on http://{HOST}:{PORT}")

    while True:
        connection, address = server_socket.accept()

        client_thread = threading.Thread(
            target=handle_client,
            args=(connection, address)
        )

        client_thread.start()

if __name__ == "__main__":
    start_server()


