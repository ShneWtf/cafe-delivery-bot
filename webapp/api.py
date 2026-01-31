"""
FastAPI backend for Telegram Cafe Web App
Provides API endpoints for menu, cart, orders
"""

import os
import sys
import hmac
import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# Add bot directory to path for database access
sys.path.insert(0, str(Path(__file__).parent.parent / "bot"))

from fastapi import FastAPI, HTTPException, Request, Query, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Import database functions
from database import (
    get_user, create_user, update_user_address,
    get_categories, get_menu_items, get_menu_item,
    get_stories, create_order, get_order, get_user_orders,
    use_user_bonus
)

app = FastAPI(title="Cafe Delivery API", version="1.0.0")

# CORS for Telegram Web App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# ============ PYDANTIC MODELS ============

class CartItem(BaseModel):
    id: int
    name: str
    price: int
    quantity: int


class OrderCreate(BaseModel):
    user_id: int
    items: List[CartItem]
    address: str
    phone: Optional[str] = None
    use_bonus: int = 0
    payment_method: str = "card"


class TelegramUser(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None


# ============ TELEGRAM VALIDATION ============

def validate_telegram_data(init_data: str) -> Optional[Dict]:
    """Validate Telegram Web App init data"""
    telegram_token = os.getenv("TELEGRAM_API_TOKEN") or os.getenv("BOT_TOKEN")
    if not telegram_token:
        return None
    
    try:
        # Parse init data
        parsed_data = {}
        for param in init_data.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                parsed_data[key] = value
        
        # Get hash
        received_hash = parsed_data.pop("hash", None)
        if not received_hash:
            return None
        
        # Sort and create data check string
        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed_data.items())
        )
        
        # Create secret key
        secret_key = hmac.new(
            b"WebAppData",
            telegram_token.encode(),
            hashlib.sha256
        ).digest()
        
        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if calculated_hash == received_hash:
            # Parse user data
            if "user" in parsed_data:
                import urllib.parse
                user_data = json.loads(urllib.parse.unquote(parsed_data["user"]))
                return user_data
        
        return None
    except Exception as e:
        print(f"Telegram validation error: {e}")
        return None


async def get_telegram_user(request: Request) -> Optional[TelegramUser]:
    """Dependency to get Telegram user from request"""
    # Try to get init data from header or query
    init_data = request.headers.get("X-Telegram-Init-Data")
    if not init_data:
        init_data = request.query_params.get("initData")
    
    if init_data:
        user_data = validate_telegram_data(init_data)
        if user_data:
            return TelegramUser(**user_data)
    
    # For development/testing - allow user_id in query
    user_id = request.query_params.get("user_id")
    if user_id:
        try:
            return TelegramUser(id=int(user_id))
        except ValueError:
            pass
    
    return None


# ============ API ENDPOINTS ============

@app.get("/")
async def root():
    """Root endpoint - serve Web App"""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Cafe Delivery API", "version": "1.0.0"}


@app.get("/app/")
async def web_app():
    """Web App endpoint"""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    raise HTTPException(status_code=404, detail="Web App not found")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@app.get("/api/user/{user_id}")
async def get_user_info(user_id: int):
    """Get user information"""
    user = get_user(user_id)
    if not user:
        # Create new user
        user = create_user(user_id, welcome_bonus=500)
    
    return {
        "id": user["telegram_id"],
        "first_name": user.get("first_name"),
        "address": user.get("address"),
        "phone": user.get("phone"),
        "balance_bonus": user.get("balance_bonus", 0),
        "balance_cashback": user.get("balance_cashback", 0)
    }


@app.get("/api/categories")
async def get_menu_categories():
    """Get all menu categories"""
    categories = get_categories()
    return {"categories": categories}


@app.get("/api/menu")
async def get_full_menu(category_id: Optional[int] = None):
    """Get menu items, optionally filtered by category"""
    items = get_menu_items(category_id)
    categories = get_categories()
    
    # Group items by category
    menu_by_category = {}
    for item in items:
        cat_id = item["category_id"]
        if cat_id not in menu_by_category:
            cat = next((c for c in categories if c["id"] == cat_id), None)
            if cat:
                menu_by_category[cat_id] = {
                    "id": cat["id"],
                    "name": cat["name"],
                    "emoji": cat["emoji"],
                    "items": []
                }
        if cat_id in menu_by_category:
            menu_by_category[cat_id]["items"].append(item)
    
    return {
        "categories": list(menu_by_category.values()),
        "all_items": items
    }


@app.get("/api/menu/{item_id}")
async def get_menu_item_detail(item_id: int):
    """Get single menu item details"""
    item = get_menu_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/api/stories")
async def get_promo_stories():
    """Get stories/promotions"""
    stories = get_stories()
    return {"stories": stories}


@app.post("/api/order")
async def create_new_order(order: OrderCreate):
    """Create new order"""
    user = get_user(order.user_id)
    if not user:
        user = create_user(order.user_id, welcome_bonus=500)
    
    # Calculate total
    total = sum(item.price * item.quantity for item in order.items)
    
    # Validate bonus usage
    bonus_used = 0
    if order.use_bonus > 0:
        if total < 500:
            raise HTTPException(
                status_code=400, 
                detail="Минимальная сумма заказа для использования бонусов: 500₽"
            )
        
        max_bonus = min(total // 2, user.get("balance_bonus", 0), order.use_bonus)
        if max_bonus > 0:
            use_user_bonus(order.user_id, max_bonus)
            bonus_used = max_bonus
            total -= bonus_used
    
    # Update address
    if order.address:
        update_user_address(order.user_id, order.address)
    
    # Create order
    items_data = [
        {"id": item.id, "name": item.name, "price": item.price, "quantity": item.quantity}
        for item in order.items
    ]
    
    order_id = create_order(
        user_id=order.user_id,
        items=items_data,
        total_price=total,
        delivery_address=order.address,
        bonus_used=bonus_used,
        payment_method=order.payment_method
    )
    
    return {
        "success": True,
        "order_id": order_id,
        "total": total,
        "bonus_used": bonus_used,
        "message": f"Заказ #{order_id} создан!"
    }


@app.get("/api/orders/{user_id}")
async def get_user_orders_list(user_id: int, limit: int = 10):
    """Get user's order history"""
    orders = get_user_orders(user_id, limit)
    return {"orders": orders}


@app.get("/api/order/{order_id}")
async def get_order_detail(order_id: int):
    """Get order details"""
    order = get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


# ============ YOOKASSA PAYMENT (PLACEHOLDER) ============

@app.post("/api/payment/create")
async def create_payment(order_id: int, amount: int):
    """Create YooKassa payment (placeholder)"""
    yookassa_shop_id = os.getenv("YOOKASSA_SHOP_ID")
    yookassa_secret = os.getenv("YOOKASSA_SECRET_KEY")
    
    if not yookassa_shop_id or not yookassa_secret:
        return {
            "success": False,
            "message": "Payment system not configured",
            "payment_url": None
        }
    
    # TODO: Implement YooKassa integration
    # from yookassa import Configuration, Payment
    # Configuration.account_id = yookassa_shop_id
    # Configuration.secret_key = yookassa_secret
    
    return {
        "success": True,
        "message": "Payment created (placeholder)",
        "payment_url": f"https://yookassa.ru/pay/{order_id}",
        "order_id": order_id,
        "amount": amount
    }


@app.post("/api/payment/webhook")
async def payment_webhook(request: Request):
    """YooKassa payment webhook"""
    # TODO: Implement webhook handling
    body = await request.json()
    print(f"Payment webhook: {body}")
    return {"status": "ok"}


# ============ RUN SERVER ============

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
