from typing import Optional, List
from fastapi import FastAPI, WebSocket
import aiohttp
from fastapi.responses import HTMLResponse
from uvicorn import run
from sqlmodel import SQLModel, create_engine, Field, Session, select
from sqlalchemy.orm import sessionmaker
import requests


class Config:
    ENGINE = create_engine("sqlite:///database.db")
    SESSION = sessionmaker(ENGINE)

    @classmethod
    def up(cls):
        SQLModel.metadata.create_all(cls.ENGINE)

    @classmethod
    def down(cls):
        SQLModel.metadata.drop_all(cls.ENGINE)


class Quote(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    author: str
    content: str


app = FastAPI(name=__name__)

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var ws = new WebSocket("ws://localhost:8000/ws");
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Message text was: {data}")


@app.post("/quotes/")
def create_quote(item: Quote):
    with Config.SESSION.begin() as session:
        session.add(item)
        return HTMLResponse(status_code=201, content="Created")


async def fetch(url):
    async with aiohttp.ClientSession() as client:
        async with client.get(url) as req:
            return await req.json()


@app.get("/quotes/", response_model=List[Quote])
async def quotes_list():
    with Config.SESSION.begin() as session:
        items = [Quote(**x.model_dump()) for x in session.scalars(select(Quote)).all()]

        req1 = await fetch("http://localhost:8001/quotes/")
        req2 = await fetch("http://localhost:8002/quotes/")

        items.extend(req1)

        items.extend(req2)
        print(f"{items=}")
        return items


if __name__ == "__main__":
    # Config.down()

    Config.up()
    run(app=app, port=8000)
