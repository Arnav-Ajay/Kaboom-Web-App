# firebase_client.py
import time
import requests
from typing import Any, Dict, Optional

FIREBASE_URL = "https://kaboom-web-app-default-rtdb.firebaseio.com"


def _make_url(path: str) -> str:
    # Ensure path starts with a slash and append .json for RTDB REST API
    if not path.startswith("/"):
        path = "/" + path
    return f"{FIREBASE_URL}{path}.json"


def fb_get(path: str) -> Any:
    url = _make_url(path)
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def fb_post(path: str, data: Dict) -> str:
    """
    POST to /rooms -> creates new child with unique key.
    Returns generated key.
    """
    url = _make_url(path)
    resp = requests.post(url, json=data)
    resp.raise_for_status()
    res = resp.json()
    return res["name"]  # Firebase returns {"name": "<key>"}


def fb_patch(path: str, data: Dict) -> None:
    url = _make_url(path)
    resp = requests.patch(url, json=data)
    resp.raise_for_status()


def fb_put(path: str, data: Any) -> None:
    url = _make_url(path)
    resp = requests.put(url, json=data)
    resp.raise_for_status()


def current_timestamp() -> float:
    return time.time()
