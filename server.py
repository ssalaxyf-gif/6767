import asyncio
import json
import os
import time

from aiohttp import web, WSMsgType


# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.environ.get(
    "REMOTE_TOKEN",
    "CHANGE_ME"
)

PORT = int(
    os.environ.get(
        "PORT",
        "8000"
    )
)

OFFLINE_AFTER = 10


# =========================================================
# CLIENTS
# =========================================================

clients = {}


# Structure:
#
# clients = {
#     "PC-001": {
#         "ws": websocket,
#         "last_seen": 1234567890.0,
#         "frame": b"..."
#     }
# }


# =========================================================
# AUTH
# =========================================================

def authorized(request):

    received_token = request.query.get(
        "token",
        ""
    )

    return (
        TOKEN != "CHANGE_ME"
        and received_token == TOKEN
    )


# =========================================================
# DASHBOARD
# =========================================================

HTML = r"""
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
            minmax(320px, 1fr)
        );

    gap: 18px;
}

.card {
    background: #111118;

    border: 1px solid #292936;
    border-radius: 16px;

    overflow: hidden;

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

    overflow: hidden;
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

<div id="counter"
     class="counter">
    Загрузка...
</div>

</header>


<main>

<div id="grid"
     class="grid">
</div>

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


const images = {};


function createCard(pcId) {

    const card =
        document.createElement("div");

    card.className = "card";


    const preview =
        document.createElement("div");

    preview.className = "preview";


    const image =
        document.createElement("img");

    image.alt = pcId;


    preview.appendChild(image);


    const info =
        document.createElement("div");

    info.className = "info";


    const name =
        document.createElement("div");

    name.className = "name";

    name.textContent = pcId;


    const status =
        document.createElement("div");

    status.className = "online";

    status.textContent = "● CONNECTING";


    info.appendChild(name);

    info.appendChild(status);


    card.appendChild(preview);

    card.appendChild(info);


    document
        .getElementById("grid")
        .appendChild(card);


    images[pcId] = {
        image: image,
        status: status
    };

}


function removeCard(pcId) {

    delete images[pcId];

}


async function loadClients() {

    try {

        const response =
            await fetch(
                "/api/clients?token=" +
                encodeURIComponent(token)
            );


        if (!response.ok) {

            throw new Error(
                "HTTP " +
                response.status
            );

        }


        const data =
            await response.json();


        renderClients(data);


    } catch (error) {

        console.error(
            "Client list error:",
            error
        );

    }

}


function renderClients(data) {

    const grid =
        document.getElementById("grid");

    const empty =
        document.getElementById("empty");

    const counter =
        document.getElementById("counter");


    grid.innerHTML = "";


    const ids =
        Object.keys(data);


    let online = 0;


    for (const pcId of ids) {

        const pc =
            data[pcId];


        const card =
            document.createElement("div");

        card.className = "card";


        const preview =
            document.createElement("div");

        preview.className = "preview";


        if (pc.online) {

            online++;


            const img =
                document.createElement("img");


            img.src =
                "/frame/" +
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

            text.textContent =
                "OFFLINE";


            preview.appendChild(text);

        }


        const info =
            document.createElement("div");

        info.className = "info";


        const name =
            document.createElement("div");

        name.className = "name";

        name.textContent =
            pcId;


        const status =
            document.createElement("div");


        if (pc.online) {

            status.className =
                "online";

            status.textContent =
                "● ONLINE";

        } else {

            status.className =
                "offline-status";

            status.textContent =
                "● OFFLINE";

        }


        info.appendChild(name);

        info.appendChild(status);


        card.appendChild(preview);

        card.appendChild(info);


        grid.appendChild(card);

    }


    if (ids.length === 0) {

        empty.style.display =
            "block";

    } else {

        empty.style.display =
            "none";

    }


    counter.textContent =
        online +
        " online / " +
        ids.length +
        " всего";

}


async function refreshFrames() {

    const ids =
        Object.keys(images);


    for (const pcId of ids) {

        const image =
            images[pcId].image;


        image.src =
            "/frame/" +
            encodeURIComponent(pcId) +
            "?token=" +
            encodeURIComponent(token) +
            "&t=" +
            Date.now();

    }

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
# INDEX
# =========================================================

async def index(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )

    return web.Response(
        text=HTML,
        content_type="text/html"
    )


# =========================================================
# CLIENT LIST
# =========================================================

async def api_clients(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    now = time.time()

    result = {}


    for pc_id, pc in clients.items():

        online = (
            now - pc["last_seen"]
            < OFFLINE_AFTER
        )


        result[pc_id] = {
            "online": online
        }


    return web.json_response(
        result
    )


# =========================================================
# FRAME
# =========================================================

async def get_frame(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    pc_id = request.match_info[
        "pc_id"
    ]


    pc = clients.get(pc_id)


    if pc is None:

        return web.Response(
            status=404,
            text="PC not found"
        )


    frame = pc.get(
        "frame"
    )


    if not frame:

        return web.Response(
            status=404,
            text="No frame"
        )


    return web.Response(
        body=frame,
        content_type="image/jpeg",
        headers={
            "Cache-Control":
                "no-cache, no-store"
        }
    )


# =========================================================
# WEBSOCKET AGENT
# =========================================================

async def agent_websocket(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    pc_id = request.query.get(
        "pc_id",
        ""
    )


    if not pc_id:

        return web.Response(
            status=400,
            text="Missing pc_id"
        )


    ws = web.WebSocketResponse(
        max_msg_size=10 * 1024 * 1024
    )


    await ws.prepare(request)


    clients[pc_id] = {
        "ws": ws,
        "last_seen": time.time(),
        "frame": None
    }


    print(
        f"[CONNECT] {pc_id}"
    )


    try:

        async for message in ws:

            if message.type == WSMsgType.BINARY:

                clients[pc_id][
                    "frame"
                ] = message.data

                clients[pc_id][
                    "last_seen"
                ] = time.time()


            elif message.type == WSMsgType.TEXT:

                try:

                    data = json.loads(
                        message.data
                    )

                    if data.get("type") == "ping":

                        clients[pc_id][
                            "last_seen"
                        ] = time.time()

                except Exception:

                    pass


            elif message.type == WSMsgType.ERROR:

                break


    except Exception as error:

        print(
            f"[WS ERROR] {pc_id}:",
            error
        )


    finally:

        current = clients.get(
            pc_id
        )


        if current is not None:

            if current["ws"] is ws:

                del clients[pc_id]


        print(
            f"[DISCONNECT] {pc_id}"
        )


    return ws


# =========================================================
# HEALTH CHECK
# =========================================================

async def health(request):

    return web.Response(
        text="OK"
    )


# =========================================================
# APPLICATION
# =========================================================

app = web.Application()


app.router.add_get(
    "/",
    index
)


app.router.add_get(
    "/health",
    health
)


app.router.add_get(
    "/api/clients",
    api_clients
)


app.router.add_get(
    "/frame/{pc_id}",
    get_frame
)


app.router.add_get(
    "/ws/agent",
    agent_websocket
)


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    print(
        "================================"
    )

    print(
        "       OFFICE MONITOR"
    )

    print(
        "================================"
    )

    print(
        "Port:",
        PORT
    )

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
