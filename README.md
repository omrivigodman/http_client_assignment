# HTTP Client - Web Resource Fetcher

This project implements a simple HTTP/1.0 client in Python using low-level TCP sockets.

The client manually creates HTTP GET requests, sends them to a server, reads and parses the HTTP response, and saves successful resources to a local output folder.

It can also detect embedded images and CSS files inside an HTML page and fetch them one by one.

## How to Run

First, make sure the web server from Assignment 1 is running.

Then open another terminal and run:

```bash
python http_client.py <host> <port> <path>
```

Example:

```bash
python http_client.py localhost 8000 /index.html
```

## Dependencies

- Python 3
- No external packages are required

The client uses only Python built-in libraries.

## Main Features

- TCP connection using Python sockets
- Manual HTTP/1.0 GET request creation
- Manual parsing of HTTP status line and headers
- Handling partial socket reads
- Reading the response body according to Content-Length
- Handling 200 OK responses
- Handling 301/302 redirects without following them
- Handling 4xx and 5xx errors without crashing
- Handling malformed HTTP responses
- Saving successful resources to the output folder
- Fetching embedded resources from `<img src="...">`
- Fetching CSS files from `<link href="...">`
- Skipping resources from external hosts
- Sequential, single-threaded resource fetching

## Output

Downloaded files are saved inside the `output` directory.

Example:

```text
output/
├── index.html
├── images/
│   └── LOGO.png
└── css/
    └── style.css
```

## Example Tests

Successful request:

```bash
python http_client.py localhost 8000 /index.html
```

404 request:

```bash
python http_client.py localhost 8000 /notfound.html
```

Forbidden path:

```bash
python http_client.py localhost 8000 /../../test.txt
```

Redirect:

```bash
python http_client.py localhost 8000 /redirect
```

Malformed response:

```bash
python http_client.py localhost 8000 /malformed
```

The HTTP response can also be compared using cURL:

```bash
curl.exe -v http://localhost:8000/index.html
```

## Demo Video

Demo video:

https://drive.google.com/file/d/1gszgHJsExBUQlAmlxtVWIXj-YE3dWgQ-/view?usp=sharing