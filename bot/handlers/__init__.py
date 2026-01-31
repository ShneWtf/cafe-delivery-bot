"""
Handlers module for Telegram Cafe Bot
"""

from .user import router as user_router
from .admin import router as admin_router
from .director import router as director_router
from .courier import router as courier_router

__all__ = ['user_router', 'admin_router', 'director_router', 'courier_router']
