"""Точка входа: uvicorn main:app --port 8080."""

from shortener.app import create_app

app = create_app()
