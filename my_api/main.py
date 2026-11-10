import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

# 로컬에선 .env를 읽고, Railway에선 Variables가 이미 들어 있음
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
FRONT_ORIGINS = [
    o.strip() for o in os.getenv("FRONT_ORIGINS", "").split(",") if o.strip()
]

sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

app = FastAPI(title="my-api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONT_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NoteIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v")
def health2():
    
    """Supabase 연결 + notes 테이블 존재 여부 확인"""
    try:
        sb.table("notes").select("id").limit(1).execute()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")


@app.get("/notes")
def list_notes():
    res = sb.table("notes").select("*").order("id", desc=True).execute()
    return res.data


@app.post("/notes", status_code=201)
def create_note(note: NoteIn):
    res = sb.table("notes").insert({"content": note.content}).execute()
    return res.data[0]


@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    sb.table("notes").delete().eq("id", note_id).execute()
    return {"deleted": note_id}
