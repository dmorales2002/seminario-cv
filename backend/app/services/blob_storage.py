"""
Vercel Blob Storage service.
Uses the Vercel Blob REST API to store and retrieve CV files.
"""
import httpx
from app.core.config import settings

_BASE_URL = "https://blob.vercel-storage.com"


def upload(filename: str, data: bytes, content_type: str) -> str:
    """Upload a file to Vercel Blob and return its public URL."""
    if not settings.BLOB_READ_WRITE_TOKEN:
        raise RuntimeError("BLOB_READ_WRITE_TOKEN is not configured.")

    response = httpx.put(
        f"{_BASE_URL}/{filename}",
        content=data,
        headers={
            "Authorization": f"Bearer {settings.BLOB_READ_WRITE_TOKEN}",
            "content-type": content_type,
        },
        params={"addRandomSuffix": "false"},
        timeout=30.0,
    )
    response.raise_for_status()
    return response.json()["url"]


def delete(url: str) -> None:
    """Delete a blob by its public URL. Silently ignores if already deleted."""
    if not settings.BLOB_READ_WRITE_TOKEN:
        return

    response = httpx.delete(
        f"{_BASE_URL}/delete",
        json={"urls": [url]},
        headers={
            "Authorization": f"Bearer {settings.BLOB_READ_WRITE_TOKEN}",
        },
        timeout=10.0,
    )
    if response.status_code != 404:
        response.raise_for_status()
