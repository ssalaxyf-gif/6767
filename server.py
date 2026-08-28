import os
import time
import json
import threading

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote


# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.environ.get("REMOTE_TOKEN", "Salaxyf_RemotePC_2026_8xK9pQ")
PORT = int(os.environ.get("PORT", "8000"))

OFFLINE_AFTER = 10


# =========================================================
# CLIENTS
# =========================================================

clients = {}
lock = threading.Lock()


# =========================================================
# DASHBOARD
# =========================================================

DASHBOARD_HTML = r"""
<!DOCTYPE html>
<html lang="ru">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>Office Monitor</title>

<style>

* {
    box-sizing: border-box;
}

body {
    margin: 0;
    background: #08080d;
    color: white;
    font-family: Arial, sans-serif;
}

header {
    height: 70px;
    padding: 0 25px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    background: #111118;
    border-bottom: 1px solid #292936;
}

.logo {
    font-size: 21px;
    font-weight: bold;
}

.counter {
    color: #aaa;
}

main {
    max-width: 1600px;
    margin: auto;
    padding: 25px;
}

.grid {
    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(300px, 1fr)
        );

    gap: 18px;
}

.card {
    background: #111118;

    border: 1px solid #292936;
    border-radius: 16px;

    overflow: hidden;
    cursor: pointer;

    transition: 0.2s;
}

.card:hover {
    transform: translateY(-3px);
    border-color: #6666ff;
}

.preview {
    width: 100%;
    aspect-ratio: 16 / 9;

    background: #030305;

    display: flex;
    align-items: center;
    justify-content: center;
}

.preview img {
    width: 100%;
    height: 100%;

    object-fit: contain;
    display: block;
}

.offline {
    color: #777;
    font-size: 18px;
}

.info {
    padding: 15px;
}

.name {
    font-size: 18px;
    font-weight: bold;
    margin-bottom: 7px;
}

.online {
    color: #5cff91;
}

.offline-status {
    color: #ff6565;
}

.empty {
    text-align: center;
    padding: 100px 20px;
    color: #777;
}

</style>

</head>

<body>

<header>

<div class="logo">
    🖥 Office Monitor
</div>

<div id="counter" class="counter">
    Загрузка...
</div>

</header>

<main>

<div id="grid" class="grid"></div>

<div id="empty"
     class="empty"
     style="display:none;">
    Нет подключённых компьютеров
</div>

</main>


<script>

const token =
    new URLSearchParams(
        window.location.search
    ).get("token");


async function loadClients() {

    try {

        const response = await fetch(
            "/api/clients?token=" +
            encodeURIComponent(token)
        );

        if (!response.ok) {
            throw new Error(
                "HTTP " + response.status
            );
        }

        const data =
            await response.json();

        renderClients(data);

    } catch (error) {

        console.error(error);

    }

}


function renderClients(clients) {

    const grid =
        document.getElementById("grid");

    const empty =
        document.getElementById("empty");

    const counter =
        document.getElementById("counter");


    grid.innerHTML = "";


    const ids =
        Object.keys(clients);


    if (ids.length === 0) {

        empty.style.display = "block";

    } else {

        empty.style.display = "none";

    }


    let online = 0;


    for (const pcId of ids) {

        const pc = clients[pcId];


        if (pc.online) {
            online++;
        }


        const card =
            document.createElement("div");

        card.className = "card";


        const preview =
            document.createElement("div");

        preview.className = "preview";


        if (pc.online) {

            const img =
                document.createElement("img");

            img.src =
                "/screen/" +
                encodeURIComponent(pcId) +
                "?token=" +
                encodeURIComponent(token) +
                "&t=" +
                Date.now();

            preview.appendChild(img);

        } else {

            const text =
                document.createElement("div");

            text.className = "offline";

            text.textContent = "OFFLINE";

            preview.appendChild(text);

        }


        const info =
            document.createElement("div");

        info.className = "info";


        const name =
            document.createElement("div");

        name.className = "name";

        name.textContent = pcId;


        const status =
            document.createElement("div");


        if (pc.online) {

            status.className = "online";
            status.textContent = "● ONLINE";

        } else {

            status.className = "offline-status";
            status.textContent = "● OFFLINE";

        }


        info.appendChild(name);
        info.appendChild(status);

        card.appendChild(preview);
        card.appendChild(info);


        card.onclick = function () {

            window.location.href =
                "/pc/" +
                encodeURIComponent(pcId) +
                "?token=" +
                encodeURIComponent(token);

        };


        grid.appendChild(card);

    }


    counter.textContent =
        online +
        " online / " +
        ids.length +
        " всего";

}


loadClients();

setInterval(
    loadClients,
    3000
);

</script>

</body>
</html>
"""


# =========================================================
# PC PAGE
# =========================================================

PC_HTML = r"""
<!DOCTYPE html>
<html lang="ru">

<head>

<meta charset="UTF-8">

<meta name="viewport"
      content="width=device-width, initial-scale=1.0">

<title>PC Monitor</title>

<style>

body {
    margin: 0;
    background: #08080d;
    color: white;
    font-family: Arial, sans-serif;
}

header {
    height: 70px;
    padding: 0 25px;

    display: flex;
    align-items: center;
    justify-content: space-between;

    background: #111118;
    border-bottom: 1px solid #292936;
}

main {
    max-width: 1500px;
    margin: auto;
    padding: 25px;
}

button {
    margin-bottom: 20px;

    padding: 12px 18px;

    border: 0;
    border-radius: 10px;

    background: #292938;
    color: white;

    cursor: pointer;
}

button:hover {
    background: #3a3a4c;
}

.screen {
    background: black;
    border-radius: 16px;
    overflow: hidden;
}

.screen img {
    width: 100%;
    display: block;
}

</style>

</head>

<body>

<header>

<div>
    🖥 <span id="pcName"></span>
</div>

<div>
    ● MONITOR
</div>

</header>


<main>

<button onclick="history.back()">
    ← Назад
</button>

<div class="screen">

<img id="screen"
     alt="Screen">

</div>

</main>


<script>

const params =
    new URLSearchParams(
        window.location.search
    );

const token =
    params.get("token");


const parts =
    window.location.pathname.split("/");


const pcId =
    decodeURIComponent(parts[2]);


document.getElementById(
    "pcName"
).textContent = pcId;


function updateScreen() {

    const image =
        document.getElementById("screen");

    image.src =
        "/screen/" +
        encodeURIComponent(pcId) +
        "?token=" +
        encodeURIComponent(token) +
        "&t=" +
        Date.now();

}


updateScreen();

setInterval(
    updateScreen,
    1000 / 30
);

</script>

</body>
</html>
"""


# =========================================================
# HTTP HANDLER
# =========================================================

class Handler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        return


    # =====================================================
    # AUTHORIZATION
    # =====================================================

    def authorized(self):

        parsed = urlparse(self.path)

        params = parse_qs(parsed.query)

        received_token = params.get(
            "token",
            [""]
        )[0]

        return (
            TOKEN != "CHANGE_ME"
            and received_token == TOKEN
        )


    # =====================================================
    # SEND HTML
    # =====================================================

    def send_html(self, html):

        data = html.encode("utf-8")

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/html; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(data))
        )

        self.end_headers()

        self.wfile.write(data)


    # =====================================================
    # GET
    # =====================================================

    def do_GET(self):

        parsed = urlparse(self.path)


        if not self.authorized():

            self.send_error(
                403,
                "Forbidden"
            )

            return


        # =================================================
        # DASHBOARD
        # =================================================

        if parsed.path == "/":

            self.send_html(
                DASHBOARD_HTML
            )

            return


        # =================================================
        # CLIENT LIST
        # =================================================

        if parsed.path == "/api/clients":

            now = time.time()

            result = {}


            with lock:

                for pc_id, pc in clients.items():

                    online = (
                        now - pc["last_seen"]
                        < OFFLINE_AFTER
                    )

                    result[pc_id] = {
                        "online": online
                    }


            data = json.dumps(
                result
            ).encode("utf-8")


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "application/json"
            )

            self.send_header(
                "Cache-Control",
                "no-cache"
            )

            self.send_header(
                "Content-Length",
                str(len(data))
            )

            self.end_headers()

            self.wfile.write(data)

            return


        # =================================================
        # PC PAGE
        # =================================================

        if parsed.path.startswith("/pc/"):

            self.send_html(
                PC_HTML
            )

            return


        # =================================================
        # SCREEN
        # =================================================

        if parsed.path.startswith("/screen/"):

            pc_id = unquote(
                parsed.path[len("/screen/"):]
            )


            with lock:

                pc = clients.get(pc_id)

                if pc is None:
                    frame = None
                else:
                    frame = pc["frame"]


            if frame is None:

                self.send_error(
                    404,
                    "No frame"
                )

                return


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "image/jpeg"
            )

            self.send_header(
                "Cache-Control",
                "no-cache, no-store"
            )

            self.send_header(
                "Content-Length",
                str(len(frame))
            )

            self.end_headers()

            self.wfile.write(frame)

            return


        self.send_error(404)


    # =====================================================
    # POST
    # =====================================================

    def do_POST(self):

        parsed = urlparse(self.path)


        # =================================================
        # FRAME
        # =================================================

        if parsed.path == "/frame":

            if not self.authorized():

                self.send_error(
                    403,
                    "Forbidden"
                )

                return


            params = parse_qs(
                parsed.query
            )


            pc_id = params.get(
                "pc_id",
                [""]
            )[0]


            if not pc_id:

                self.send_error(
                    400,
                    "Missing pc_id"
                )

                return


            try:

                length = int(
                    self.headers.get(
                        "Content-Length",
                        "0"
                    )
                )

            except ValueError:

                self.send_error(
                    400,
                    "Invalid Content-Length"
                )

                return


            if length <= 0:

                self.send_error(
                    400,
                    "Empty frame"
                )

                return


            frame = self.rfile.read(
                length
            )


            if not frame:

                self.send_error(
                    400,
                    "Empty frame"
                )

                return


            with lock:

                clients[pc_id] = {
                    "frame": frame,
                    "last_seen": time.time()
                }


            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/plain"
            )

            self.send_header(
                "Content-Length",
                "2"
            )

            self.end_headers()

            self.wfile.write(b"OK")

            return


        self.send_error(404)


# =========================================================
# START SERVER
# =========================================================

print("================================")
print("       OFFICE MONITOR")
print("================================")
print("Port:", PORT)


server = ThreadingHTTPServer(
    ("0.0.0.0", PORT),
    Handler
)


print("Server started")


try:

    server.serve_forever()

except KeyboardInterrupt:

    print("Stopping server...")

finally:

    server.server_close()