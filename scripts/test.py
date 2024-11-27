import atexit
import http.server
import json
import logging
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from fake_useragent import UserAgent
from tqdm import tqdm
from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from uvicorn import Config, Server

ua = UserAgent()

PORT = 37491


app = FastAPI()

@app.get("/")
async def root(request: Request):
    user_agent = request.headers.get("user-agent")

    if not all(c == 'F' for c in user_agent):
        return Response(status_code=400)

    return Response(content=str(len(user_agent)).encode())

def start_server():
    config = Config(app=app, host="::1", port=PORT)
    server = Server(config)
    server.run()

def start_ua2f(u: str):
    p = subprocess.Popen([u])
    atexit.register(lambda: p.kill())


def setup_iptables():
    os.system(f"sudo iptables -A OUTPUT -p tcp --dport {PORT} -j NFQUEUE --queue-num 10010")
    os.system(f"sudo ip6tables -A OUTPUT -p tcp --dport {PORT} -j NFQUEUE --queue-num 10010")


def cleanup_iptables():
    os.system(f"sudo iptables -D OUTPUT -p tcp --dport {PORT} -j NFQUEUE --queue-num 10010")
    os.system(f"sudo ip6tables -D OUTPUT -p tcp --dport {PORT} -j NFQUEUE --queue-num 10010")


if __name__ == "__main__":
    if os.name != 'posix':
        raise Exception("This script only supports Linux")

    if os.geteuid() != 0:
        raise Exception("This script requires root privileges")

    ua2f = sys.argv[1]

    setup_iptables()

    server = threading.Thread(target=start_server)
    server.daemon = True
    server.start()

    ua2f_thread = threading.Thread(target=start_ua2f, args=(ua2f,))
    ua2f_thread.daemon = True
    ua2f_thread.start()

    print(f"Starting UA2F: {ua2f}")

    time.sleep(3)

    for i in tqdm(range(2000)):
        nxt = ua.random
        response = requests.get(f"http://127.0.0.1:{PORT}", headers={
            "User-Agent": nxt
        })
        assert response.ok
        assert response.text == str(len(nxt))

    for i in tqdm(range(2000)):
        nxt = ua.random
        response = requests.get(f"http://[::1]:{PORT}", headers={
            "User-Agent": nxt
        })
        assert response.ok
        assert response.text == str(len(nxt))

    # clean
    cleanup_iptables()
