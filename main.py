from fastapi import FastAPI

from routers import documents, query

app = FastAPI(title="DocMind")

app.include_router(documents.router)
app.include_router(query.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
