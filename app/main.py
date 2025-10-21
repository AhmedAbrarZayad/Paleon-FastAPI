from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
async def read_root():
    return {"Hello": "World"}

@app.post("/fossil-image/")
async def get_rag_output(
    image_file: list[UploadFile] = File(...)
):
    print(f"Received file: {len(image_file)} files")

