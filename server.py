import json
import os
import time
import uuid

from aiohttp import web, WSMsgType


# =========================================================
# SETTINGS
# =========================================================

TOKEN = os.environ.get(
    "REMOTE_TOKEN",
    "Salaxyf_RemotePC_2026_8xK9pQ"
)

PORT = int(
    os.environ.get(
        "PORT",
        "8000"
    )
)

OFFLINE_AFTER = 15


# =========================================================
# CLIENTS
# =========================================================

clients = {}

agents = {}
viewers = {}


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

    border-bottom:
        1px solid #292936;
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

    border:
        1px solid #292936;

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

    overflow: hidden;
}

.preview video {
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


const activeConnections = {};


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
            "CLIENT LIST ERROR:",
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


        if (pc.online) {

            online++;

        }


        const card =
            document.createElement("div");

        card.className = "card";


        const preview =
            document.createElement("div");

        preview.className =
            "preview";


        if (pc.online) {

            const video =
                document.createElement("video");


            video.autoplay = true;

            video.playsInline = true;

            video.muted = true;


            preview.appendChild(
                video
            );


            startWebRTC(
                pcId,
                video
            );

        } else {

            const text =
                document.createElement("div");

            text.className =
                "offline";

            text.textContent =
                "OFFLINE";


            preview.appendChild(
                text
            );

        }


        const info =
            document.createElement("div");

        info.className =
            "info";


        const name =
            document.createElement("div");

        name.className =
            "name";

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


async function startWebRTC(
    pcId,
    video
) {

    if (activeConnections[pcId]) {

        try {

            activeConnections[
                pcId
            ].close();

        } catch {}

    }


    const viewerId =
        crypto.randomUUID();


    const protocol =
        location.protocol === "https:"
            ? "wss:"
            : "ws:";


    const ws =
        new WebSocket(
            protocol +
            "//" +
            location.host +
            "/ws/signal?role=viewer" +
            "&pc_id=" +
            encodeURIComponent(pcId) +
            "&viewer_id=" +
            viewerId +
            "&token=" +
            encodeURIComponent(token)
        );


    const pc =
        new RTCPeerConnection({
            iceServers: [
                {
                    urls:
                        "stun:stun.l.google.com:19302"
                }
            ]
        });


    activeConnections[
        pcId
    ] = pc;


    pc.addTransceiver(
        "video",
        {
            direction: "recvonly"
        }
    );


    pc.ontrack = function(event) {

        if (event.streams.length > 0) {

            video.srcObject =
                event.streams[0];

        }

    };


    ws.onmessage =
        async function(event) {

            const message =
                JSON.parse(
                    event.data
                );


            if (
                message.type ===
                "answer"
            ) {

                await pc.setRemoteDescription(
                    {
                        type: "answer",
                        sdp: message.sdp
                    }
                );

            }

        };


    ws.onopen =
        async function() {

            const offer =
                await pc.createOffer();


            await pc.setLocalDescription(
                offer
            );


            await waitForIceGathering(
                pc
            );


            ws.send(
                JSON.stringify({
                    type: "offer",

                    sdp:
                        pc.localDescription.sdp
                })
            );

        };


    ws.onclose =
        function() {

            try {

                pc.close();

            } catch {}

        };

}


function waitForIceGathering(
    pc
) {

    return new Promise(
        resolve => {

            if (
                pc.iceGatheringState ===
                "complete"
            ) {

                resolve();

                return;

            }


            function check() {

                if (
                    pc.iceGatheringState ===
                    "complete"
                ) {

                    pc.removeEventListener(
                        "icegatheringstatechange",
                        check
                    );

                    resolve();

                }

            }


            pc.addEventListener(
                "icegatheringstatechange",
                check
            );

        }
    );

}


loadClients();


setInterval(
    loadClients,
    5000
);

</script>

</body>

</html>
"""


# =========================================================
# AUTH
# =========================================================

def authorized(request):

    received =
        request.query.get(
            "token",
            ""
        )

    return (
        TOKEN != "CHANGE_ME"
        and
        received == TOKEN
    )


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


    for pc_id, data in clients.items():

        result[pc_id] = {
            "online":
                now - data["last_seen"]
                < OFFLINE_AFTER
        }


    return web.json_response(
        result
    )


# =========================================================
# SIGNALING WEBSOCKET
# =========================================================

async def signal(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    role =
        request.query.get(
            "role",
            ""
        )


    pc_id =
        request.query.get(
            "pc_id",
            ""
        )


    viewer_id =
        request.query.get(
            "viewer_id",
            ""
        )


    if role not in (
        "agent",
        "viewer"
    ):

        return web.Response(
            status=400,
            text="Invalid role"
        )


    if not pc_id:

        return web.Response(
            status=400,
            text="Missing pc_id"
        )


    ws =
        web.WebSocketResponse(
            heartbeat=30
        )


    await ws.prepare(request)


    if role == "agent":

        agents[pc_id] = ws


        clients[pc_id] = {
            "last_seen":
                time.time()
        }


        print(
            "[AGENT CONNECTED]",
            pc_id
        )


    else:

        if not viewer_id:

            await ws.close()

            return ws


        viewers[
            (pc_id, viewer_id)
        ] = ws


        print(
            "[VIEWER CONNECTED]",
            pc_id,
            viewer_id
        )


    try:

        async for message in ws:

            if (
                message.type !=
                WSMsgType.TEXT
            ):

                continue


            try:

                data =
                    json.loads(
                        message.data
                    )

            except Exception:

                continue


            if role == "agent":

                clients[pc_id][
                    "last_seen"
                ] = time.time()


                target =
                    data.get(
                        "viewer_id"
                    )


                if target:

                    viewer =
                        viewers.get(
                            (
                                pc_id,
                                target
                            )
                        )


                    if viewer:

                        await viewer.send_str(
                            json.dumps(data)
                        )


            else:

                agent =
                    agents.get(
                        pc_id
                    )


                if agent:

                    data[
                        "viewer_id"
                    ] = viewer_id


                    await agent.send_str(
                        json.dumps(data)
                    )


    except Exception as error:

        print(
            "[SIGNAL ERROR]",
            error
        )


    finally:

        if role == "agent":

            if agents.get(
                pc_id
            ) is ws:

                del agents[pc_id]


            clients.pop(
                pc_id,
                None
            )


            print(
                "[AGENT DISCONNECTED]",
                pc_id
            )


        else:

            viewers.pop(
                (
                    pc_id,
                    viewer_id
                ),
                None
            )


            print(
                "[VIEWER DISCONNECTED]",
                pc_id,
                viewer_id
            )


    return ws


# =========================================================
# HEALTH
# =========================================================

async def health(request):

    return web.Response(
        text="OK"
    )


# =========================================================
# APP
# =========================================================

app =
    web.Application()


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
    "/ws/signal",
    signal
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
