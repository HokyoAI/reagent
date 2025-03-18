from reagent.core import Agent, Catalog, Identity

# chatbot = Agent()

catalog = Catalog(None, True, True)
# catalog.add_taskable(taskable=chatbot)
catalog.finalize()


async def http_authenticate(username: str) -> Identity | None:
    # Placeholder for actual authentication logic
    return None, {"username": username}


app = catalog.api(http_authenticate=http_authenticate)

if __name__ == "__main__":
    # Run the FastAPI app using Uvicorn
    import uvicorn

    uvicorn.run(app)
