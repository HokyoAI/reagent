import uvicorn
from fastapi import FastAPI

# from reagent.core.agent import Agent
from reagent.core.catalog import Catalog, Labels

# chatbot = Agent()

catalog = Catalog(None, True, True)
# catalog.add_taskable(taskable=chatbot)
catalog.finalize()


async def http_authenticate(username: str) -> tuple[str | None, Labels] | None:
    # Placeholder for actual authentication logic
    return None, {"username": username}


router, lifespan = catalog.router(http_authenticate=http_authenticate)

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    # Run the FastAPI app using Uvicorn
    uvicorn.run(app)
