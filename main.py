from fastapi import *
from unit import example
import uvicorn

app = FastAPI()


@app.get("/")
def test():
    return example()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)