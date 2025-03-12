import uvicorn

from reagent.core.api.server import app


def main(host: str, port: int):
    uvicorn.run(app, host=host, port=port)
