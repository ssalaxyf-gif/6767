import json
import os
import time

from aiohttp import web, WSMsgType


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


agents = {}
clients = {}


HTML = r"""
<!DOCTYPE html>
<html lang="ru">

<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

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
        repeat(auto-fit, minmax(360px, 1fr));
    gap: 20px;
}

.card {
    background: #111118;
    border: 1px solid #292936;
    border-radius: 16px;
    overflow: hidden;
}

.preview {
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #020204;

    display: flex;
    align-items: center;
    justify-content: center;
}

video {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
}

.info {
    padding: 14px;
}

.name {
    font-size: 18px;
    font-weight: bold;
}

.online {
    margin-top: 6px;
    color: #5cff91;
}

.offline {
    margin-top: 6px;
    color: #ff6565;
}

.waiting {
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

</main>

<script>

const token =
    new URLSearchParams(
        location.search
    ).get("token");


const connections = {};


async function getClients() {

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

        return await response.json();

    } catch (error) {

        console.error(error);

        return {};

    }
}


async function createConnection(
    pcId,
    video
) {

    if (connections[pcId]) {

        try {
            connections[pcId].pc.close();
            connections[pcId].ws.close();
        } catch {}

    }


    const protocol =
        location.protocol === "https:"
            ? "wss:"
            : "ws:";


    const ws = new WebSocket(
        protocol +
        "//" +
        location.host +
        "/ws/viewer" +
        "?token=" +
        encodeURIComponent(token) +
        "&pc_id=" +
        encodeURIComponent(pcId)
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


    connections[pcId] = {
        pc: pc,
        ws: ws
    };


    pc.addTransceiver(
        "video",
        {
            direction: "recvonly"
        }
    );


    pc.ontrack = function(event) {

        if (event.streams.length) {

            video.srcObject =
                event.streams[0];

            video.play().catch(() => {});

        }

    };


    pc.onconnectionstatechange =
        function() {

            console.log(
                pcId,
                "WebRTC:",
                pc.connectionState
            );

        };


    ws.onopen = async function() {

        try {

            const offer =
                await pc.createOffer();

            await pc.setLocalDescription(
                offer
            );

            await waitForIce(pc);


            ws.send(
                JSON.stringify({
                    type: "offer",
                    sdp:
                        pc.localDescription.sdp
                })
            );

        } catch (error) {

            console.error(
                "Offer error:",
                error
            );

        }

    };


    ws.onmessage = async function(event) {

        try {

            const message =
                JSON.parse(event.data);


            if (
                message.type === "answer"
            ) {

                await pc.setRemoteDescription({
                    type: "answer",
                    sdp: message.sdp
                });

            }

        } catch (error) {

            console.error(
                "Signal error:",
                error
            );

        }

    };


    ws.onclose = function() {

        console.log(
            "Viewer signaling closed:",
            pcId
        );

    };

}


function waitForIce(pc) {

    return new Promise(resolve => {

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

    });

}


async function render() {

    const data =
        await getClients();


    const grid =
        document.getElementById("grid");


    const counter =
        document.getElementById("counter");


    grid.innerHTML = "";


    const ids =
        Object.keys(data);


    let online = 0;


    for (const pcId of ids) {

        const pc = data[pcId];


        const card =
            document.createElement("div");

        card.className = "card";


        const preview =
            document.createElement("div");

        preview.className = "preview";


        if (pc.online) {

            online++;


            const video =
                document.createElement("video");

            video.autoplay = true;
            video.playsInline = true;
            video.muted = true;


            preview.appendChild(video);


            createConnection(
                pcId,
                video
            );

        } else {

            const text =
                document.createElement("div");

            text.className =
                "waiting";

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

        name.textContent = pcId;


        const status =
            document.createElement("div");


        if (pc.online) {

            status.className = "online";

            status.textContent =
                "● ONLINE";

        } else {

            status.className = "offline";

            status.textContent =
                "● OFFLINE";

        }


        info.appendChild(name);
        info.appendChild(status);


        card.appendChild(preview);
        card.appendChild(info);


        grid.appendChild(card);

    }


    counter.textContent =
        online +
        " online / " +
        ids.length +
        " всего";

}


render();


setInterval(
    render,
    10000
);

</script>

</body>
</html>
"""


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


async def api_clients(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    now = time.time()

    result = {}


    for pc_id, data in clients.items():

        online = (
            now - data["last_seen"]
            < OFFLINE_AFTER
        )


        result[pc_id] = {
            "online": online
        }


    return web.json_response(result)


async def agent_ws(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    pc_id =
        request.query.get(
            "pc_id",
            ""
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


    agents[pc_id] = ws


    clients[pc_id] = {
        "last_seen": time.time()
    }


    print(
        "[AGENT CONNECTED]",
        pc_id
    )


    try:

        async for message in ws:

            if message.type != WSMsgType.TEXT:
                continue


            clients[pc_id][
                "last_seen"
            ] = time.time()


            try:

                data =
                    json.loads(
                        message.data
                    )

            except Exception:

                continue


            viewer_id =
                data.get(
                    "viewer_id"
                )


            if viewer_id:

                viewer =
                    viewers.get(
                        (
                            pc_id,
                            viewer_id
                        )
                    )


                if viewer:

                    await viewer.send_str(
                        json.dumps(data)
                    )

    finally:

        if agents.get(pc_id) is ws:

            agents.pop(
                pc_id,
                None
            )


        clients.pop(
            pc_id,
            None
        )


        print(
            "[AGENT DISCONNECTED]",
            pc_id
        )


    return ws


viewers = {}


async def viewer_ws(request):

    if not authorized(request):

        return web.Response(
            status=403,
            text="Forbidden"
        )


    pc_id =
        request.query.get(
            "pc_id",
            ""
        )


    if not pc_id:

        return web.Response(
            status=400,
            text="Missing pc_id"
        )


    agent =
        agents.get(pc_id)


    if agent is None:

        return web.Response(
            status=404,
            text="Agent offline"
        )


    viewer_id =
        os.urandom(8).hex()


    ws =
        web.WebSocketResponse(
            heartbeat=30
        )


    await ws.prepare(request)


    viewers[
        (
            pc_id,
            viewer_id
        )
    ] = ws


    try:

        async for message in ws:

            if message.type != WSMsgType.TEXT:
                continue


            try:

                data =
                    json.loads(
                        message.data
                    )

            except Exception:

                continue


            data["viewer_id"] =
                viewer_id


            await agent.send_str(
                json.dumps(data)
            )

    finally:

        viewers.pop(
            (
                pc_id,
                viewer_id
            ),
            None
        )


    return ws


async def health(request):

    return web.Response(
        text="OK"
    )


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
    "/ws/agent",
    agent_ws
)

app.router.add_get(
    "/ws/viewer",
    viewer_ws
)


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
        "PORT:",
        PORT
    )

    web.run_app(
        app,
        host="0.0.0.0",
        port=PORT
    )
