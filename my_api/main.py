import os
import re
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import create_client

load_dotenv()

# 로컬에선 .env를 읽고, Railway에선 Variables가 이미 들어 있음
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SECRET_KEY = os.environ["SUPABASE_SECRET_KEY"]
FRONT_ORIGINS = [
    o.strip() for o in os.getenv("FRONT_ORIGINS", "").split(",") if o.strip()
]
# 개발 편의: 로컬 프론트는 항상 허용
LOCAL_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

sb = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

app = FastAPI(title="my-api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(FRONT_ORIGINS + LOCAL_ORIGINS)),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_QTY = 99
FREE_SHIPPING_FROM = 50000
SHIPPING_FEE = 3000
CART_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def valid_cart_id(cart_id: str) -> str:
    if not CART_ID_RE.match(cart_id):
        raise HTTPException(status_code=400, detail="올바르지 않은 cart_id 입니다.")
    return cart_id


def db_error(e: Exception) -> HTTPException:
    return HTTPException(status_code=500, detail=f"DB 오류: {e}")


# ---------- 상태 확인 ----------
@app.get("/")
def root():
    """주소창에 백엔드 주소만 열었을 때 보이는 안내"""
    return {
        "name": "my-api",
        "status": "ok",
        "docs": "/docs",
        "endpoints": ["/health", "/health/db", "/products", "/cart/{cart_id}", "/notes"],
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
@app.get("/v")
def health_db():
    """Supabase 연결 + 테이블 존재 여부 확인"""
    try:
        sb.table("products").select("id").limit(1).execute()
        sb.table("cart_items").select("id").limit(1).execute()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        raise db_error(e)


# ---------- 메모 (기존 기능) ----------
class NoteIn(BaseModel):
    content: str = Field(min_length=1, max_length=500)


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


# ---------- 상품 ----------
@app.get("/products")
def list_products(category: Optional[str] = Query(default=None, max_length=30)):
    try:
        q = sb.table("products").select("*").order("id")
        if category:
            q = q.eq("category", category)
        return q.execute().data
    except Exception as e:
        raise db_error(e)


# ---------- 장바구니 ----------
class CartItemIn(BaseModel):
    product_id: int = Field(ge=1)
    quantity: int = Field(default=1, ge=1, le=MAX_QTY)


class QuantityIn(BaseModel):
    quantity: int = Field(ge=1, le=MAX_QTY)


def build_cart(cart_id: str) -> dict:
    """장바구니 내용과 금액 합계를 계산해서 돌려줍니다."""
    rows = (
        sb.table("cart_items")
        .select("quantity, created_at, product:products(id, name, emoji, category, price)")
        .eq("cart_id", cart_id)
        .order("created_at")
        .execute()
        .data
    )
    items = []
    for r in rows:
        p = r["product"]
        items.append(
            {
                "product_id": p["id"],
                "name": p["name"],
                "emoji": p["emoji"],
                "category": p["category"],
                "price": p["price"],
                "quantity": r["quantity"],
                "subtotal": p["price"] * r["quantity"],
            }
        )
    subtotal = sum(i["subtotal"] for i in items)
    shipping = 0 if (subtotal == 0 or subtotal >= FREE_SHIPPING_FROM) else SHIPPING_FEE
    return {
        "cart_id": cart_id,
        "items": items,
        "total_quantity": sum(i["quantity"] for i in items),
        "subtotal": subtotal,
        "shipping": shipping,
        "total": subtotal + shipping,
        "free_shipping_from": FREE_SHIPPING_FROM,
    }


@app.get("/cart/{cart_id}")
def get_cart(cart_id: str = Path(...)):
    valid_cart_id(cart_id)
    try:
        return build_cart(cart_id)
    except Exception as e:
        raise db_error(e)


@app.post("/cart/{cart_id}/items")
def add_to_cart(item: CartItemIn, cart_id: str = Path(...)):
    valid_cart_id(cart_id)
    try:
        product = (
            sb.table("products").select("id").eq("id", item.product_id).execute().data
        )
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

        existing = (
            sb.table("cart_items")
            .select("id, quantity")
            .eq("cart_id", cart_id)
            .eq("product_id", item.product_id)
            .execute()
            .data
        )
        if existing:
            new_qty = min(existing[0]["quantity"] + item.quantity, MAX_QTY)
            sb.table("cart_items").update(
                {"quantity": new_qty, "updated_at": now_iso()}
            ).eq("id", existing[0]["id"]).execute()
        else:
            sb.table("cart_items").insert(
                {
                    "cart_id": cart_id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                }
            ).execute()
        return build_cart(cart_id)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)


@app.patch("/cart/{cart_id}/items/{product_id}")
def set_quantity(body: QuantityIn, cart_id: str = Path(...), product_id: int = Path(..., ge=1)):
    valid_cart_id(cart_id)
    try:
        res = (
            sb.table("cart_items")
            .update({"quantity": body.quantity, "updated_at": now_iso()})
            .eq("cart_id", cart_id)
            .eq("product_id", product_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="장바구니에 없는 상품입니다.")
        return build_cart(cart_id)
    except HTTPException:
        raise
    except Exception as e:
        raise db_error(e)


@app.delete("/cart/{cart_id}/items/{product_id}")
def remove_item(cart_id: str = Path(...), product_id: int = Path(..., ge=1)):
    valid_cart_id(cart_id)
    try:
        sb.table("cart_items").delete().eq("cart_id", cart_id).eq(
            "product_id", product_id
        ).execute()
        return build_cart(cart_id)
    except Exception as e:
        raise db_error(e)


@app.delete("/cart/{cart_id}")
def clear_cart(cart_id: str = Path(...)):
    valid_cart_id(cart_id)
    try:
        sb.table("cart_items").delete().eq("cart_id", cart_id).execute()
        return build_cart(cart_id)
    except Exception as e:
        raise db_error(e)
