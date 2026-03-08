#!/usr/bin/env python3
import asyncio
import copy
import json
import math
import os
import re
import shutil
import socket
import time
from html import unescape
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import numpy as np
import qrcode
import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas


ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
COURSES_DIR = DATA_DIR / "courses"
STATE_FILE = DATA_DIR / "state.json"
ENV_FILE = ROOT / ".env"
PORT = 8080
CHAT_MAX_CONCURRENCY = 5
CHAT_INACTIVITY_SECONDS = 30
PDF_MAX_FILES_PER_COURSE = 20
PDF_MAX_SIZE_BYTES = 30 * 1024 * 1024
MODEL_PATH = Path(
    (Path(os.environ.get("MAXBOARD_MODEL_PATH", "")).expanduser())
    if os.environ.get("MAXBOARD_MODEL_PATH")
    else "/Users/stt/GIT/models/qwen2.5-3b-instruct-q4_k_m.gguf"
)
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
LLM_PROVIDER = (os.environ.get("MAXBOARD_LLM_PROVIDER", "local") or "local").strip().lower()
APERTUS_REMOTE_API_URL = (os.environ.get("MAXBOARD_APERTUS_API_URL", "") or "").strip()
APERTUS_REMOTE_API_KEY = (os.environ.get("MAXBOARD_APERTUS_API_KEY", "") or "").strip()
INFOMANIAK_PRODUCT_ID = (os.environ.get("MAXBOARD_INFOMANIAK_PRODUCT_ID", "") or "").strip()
INFOMANIAK_API_TOKEN = (os.environ.get("MAXBOARD_INFOMANIAK_API_TOKEN", "") or "").strip()
APERTUS_MODEL = (os.environ.get("MAXBOARD_APERTUS_MODEL", "meta-llama/Llama-3.3-70B-Instruct") or "meta-llama/Llama-3.3-70B-Instruct").strip()


app = FastAPI(title="MaxBoard")
state_lock = asyncio.Lock()
clients_lock = asyncio.Lock()
clients: list[WebSocket] = []
client_roles: dict[int, str] = {}
state: dict[str, Any] = {}
_llm = None
_embedder = None
course_rag_cache: dict[str, list[dict[str, Any]]] = {}
pdf_reindex_state: dict[str, dict[str, Any]] = {}

chat_lock = asyncio.Lock()
chat_cond = asyncio.Condition(chat_lock)
chat_queue: list[str] = []
chat_active: set[str] = set()
chat_sessions: dict[str, dict[str, Any]] = {}
chat_prompts_session = 0


@app.middleware("http")
async def disable_http_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


class CreateCourseBody(BaseModel):
    name: str


class RenameBody(BaseModel):
    name: str


class ReorderCoursesBody(BaseModel):
    courseIds: list[str]


class CreateWhiteboardBody(BaseModel):
    name: str


class DuplicateWhiteboardBody(BaseModel):
    targetCourseId: Optional[str] = None


class ReorderWhiteboardsBody(BaseModel):
    whiteboardIds: list[str]


class ActivateWhiteboardBody(BaseModel):
    whiteboardId: str


class ExportPdfHotspot(BaseModel):
    title: str = ""
    html: str = ""


class ExportPdfBody(BaseModel):
    courseName: str = ""
    whiteboardName: str = ""
    imageDataUrl: str
    hotspots: list[ExportPdfHotspot] = []


class ImportWhiteboardBody(BaseModel):
    payload: dict[str, Any]
    targetCourseId: Optional[str] = None
    name: Optional[str] = None


class RenamePdfBody(BaseModel):
    newName: str


class ChatAskBody(BaseModel):
    sessionId: str
    studentName: str
    courseId: str
    whiteboardId: str
    hotspotId: str
    hotspotTitle: str = ""
    hotspotHtml: str = ""
    allHotspots: list[dict[str, Any]] = []
    prompt: str


class ChatReleaseBody(BaseModel):
    sessionId: str


class LlmConfigBody(BaseModel):
    provider: str = "local"
    apertusModel: str = ""


def now_ms() -> int:
    return int(time.time() * 1000)


def make_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


def sanitize_name(name: str, fallback: str) -> str:
    v = (name or "").strip()
    return v[:120] if v else fallback


def detect_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def sanitize_filename(name: str, fallback: str = "document.pdf") -> str:
    raw = re.sub(r"[^A-Za-z0-9_. -]", "_", (name or "").strip())
    raw = raw.replace(" ", "_")
    if not raw:
        raw = fallback
    if not raw.lower().endswith(".pdf"):
        raw += ".pdf"
    return raw[:180]


def normalize_llm_provider(raw: str) -> str:
    v = (raw or "").strip().lower()
    return v if v in {"local", "apertus"} else "local"


def default_llm_config() -> dict[str, Any]:
    return {
        "provider": normalize_llm_provider(LLM_PROVIDER),
        "apertusModel": APERTUS_MODEL,
    }


def current_llm_config() -> dict[str, Any]:
    cfg = state.get("llm", {}) if isinstance(state, dict) else {}
    provider = normalize_llm_provider(str(cfg.get("provider", default_llm_config()["provider"])))
    model = str(cfg.get("apertusModel", APERTUS_MODEL) or APERTUS_MODEL).strip()
    return {"provider": provider, "apertusModel": model}


def read_env_file_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            out[key.strip()] = value.strip()
    except Exception:
        return {}
    return out


def course_dir(course_id: str) -> Path:
    return COURSES_DIR / str(course_id)


def course_pdf_dir(course_id: str) -> Path:
    return course_dir(course_id) / "pdfs"


def course_index_file(course_id: str) -> Path:
    return course_dir(course_id) / "pdf_index.json"


def get_llm():
    global _llm
    if _llm is not None:
        return _llm
    if not MODEL_PATH.exists():
        raise HTTPException(503, f"Modèle introuvable: {MODEL_PATH}")
    try:
        from llama_cpp import Llama
    except Exception as exc:
        raise HTTPException(503, f"llama-cpp-python indisponible: {exc}")
    _llm = Llama(model_path=str(MODEL_PATH), n_ctx=8192, n_gpu_layers=-1, verbose=False)
    return _llm


def resolve_apertus_url() -> str:
    if APERTUS_REMOTE_API_URL:
        return APERTUS_REMOTE_API_URL.rstrip("/")
    if INFOMANIAK_PRODUCT_ID:
        return f"https://api.infomaniak.com/1/ai/{INFOMANIAK_PRODUCT_ID}/openai"
    env_values = read_env_file_values(ENV_FILE)
    file_remote = (
        env_values.get("MAXBOARD_APERTUS_API_URL")
        or env_values.get("KIRALM_REMOTE_API_URL")
        or ""
    ).strip()
    if file_remote:
        return file_remote.rstrip("/")
    file_product_id = (
        env_values.get("MAXBOARD_INFOMANIAK_PRODUCT_ID")
        or env_values.get("KIRALM_INFOMANIAK_PRODUCT_ID")
        or ""
    ).strip()
    if file_product_id:
        return f"https://api.infomaniak.com/1/ai/{file_product_id}/openai"
    return ""


def resolve_apertus_api_key() -> str:
    in_memory = (APERTUS_REMOTE_API_KEY or INFOMANIAK_API_TOKEN).strip()
    if in_memory:
        return in_memory
    env_values = read_env_file_values(ENV_FILE)
    return (
        env_values.get("MAXBOARD_APERTUS_API_KEY")
        or env_values.get("MAXBOARD_INFOMANIAK_API_TOKEN")
        or env_values.get("KIRALM_REMOTE_API_KEY")
        or env_values.get("KIRALM_INFOMANIAK_API_TOKEN")
        or ""
    ).strip()


def chat_completion_apertus(messages: list[dict[str, str]], model_name: str) -> str:
    base = resolve_apertus_url()
    api_key = resolve_apertus_api_key()
    if not base:
        raise HTTPException(503, "Apertus non configuré: URL absente")
    if not api_key:
        raise HTTPException(503, "Apertus non configuré: token API absent")
    endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
    adapted_messages: list[dict[str, str]] = []
    system_parts: list[str] = []
    for msg in messages:
        role = str(msg.get("role", "")).strip().lower()
        content = str(msg.get("content", "")).strip()
        if not content:
            continue
        if role == "system":
            system_parts.append(content)
            continue
        if role in {"user", "assistant"}:
            adapted_messages.append({"role": role, "content": content})
    if system_parts:
        preamble = "Contexte et consignes:\n" + "\n\n".join(system_parts)
        adapted_messages.insert(0, {"role": "user", "content": preamble})
    if not adapted_messages:
        adapted_messages = [{"role": "user", "content": "Bonjour"}]

    payload = {
        "model": model_name or APERTUS_MODEL,
        "messages": adapted_messages,
        "temperature": 0.2,
        "max_tokens": 500,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=120)
    except Exception as exc:
        raise HTTPException(502, f"Erreur réseau Apertus: {exc}")
    if resp.status_code >= 400:
        snippet = resp.text[:300] if resp.text else ""
        raise HTTPException(502, f"Apertus HTTP {resp.status_code}: {snippet}")
    try:
        data = resp.json()
        return str(data["choices"][0]["message"]["content"]).strip()
    except Exception as exc:
        raise HTTPException(502, f"Réponse Apertus invalide: {exc}")


def get_embedder():
    global _embedder
    if _embedder is not None:
        return _embedder
    try:
        from fastembed import TextEmbedding
    except Exception as exc:
        raise HTTPException(503, f"fastembed indisponible: {exc}")
    _embedder = TextEmbedding(model_name=EMBED_MODEL)
    return _embedder


def split_text_chunks(text: str, chunk_size: int = 900, overlap: int = 140) -> list[str]:
    src = re.sub(r"\s+", " ", text or "").strip()
    if not src:
        return []
    chunks: list[str] = []
    i = 0
    n = len(src)
    while i < n:
        j = min(n, i + chunk_size)
        piece = src[i:j].strip()
        if piece:
            chunks.append(piece)
        if j >= n:
            break
        i = max(i + 1, j - overlap)
    return chunks


def load_course_index(course_id: str) -> list[dict[str, Any]]:
    if course_id in course_rag_cache:
        return course_rag_cache[course_id]
    idx_file = course_index_file(course_id)
    if not idx_file.exists():
        course_rag_cache[course_id] = []
        return []
    try:
        payload = json.loads(idx_file.read_text(encoding="utf-8"))
        chunks = payload.get("chunks", [])
        hydrated: list[dict[str, Any]] = []
        for c in chunks:
            emb = c.get("embedding")
            if not isinstance(emb, list):
                continue
            item = {
                "source": c.get("source", ""),
                "page": int(c.get("page", 0)),
                "text": c.get("text", ""),
                "vec": np.array(emb, dtype=np.float32),
            }
            hydrated.append(item)
        course_rag_cache[course_id] = hydrated
        return hydrated
    except Exception:
        course_rag_cache[course_id] = []
        return []


def cosine_score(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-8:
        return 0.0
    return float(np.dot(a, b) / denom)


def retrieve_course_rag(course_id: str, query: str, top_k: int = 4) -> list[dict[str, Any]]:
    chunks = load_course_index(course_id)
    if not chunks:
        return []
    embedder = get_embedder()
    qvec = np.array(list(embedder.embed([query]))[0], dtype=np.float32)
    scored: list[tuple[float, dict[str, Any]]] = []
    for c in chunks:
        vec = c.get("vec")
        if vec is None:
            continue
        scored.append((cosine_score(qvec, vec), c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:top_k] if score > 0.05]


def rebuild_course_index_sync(course_id: str) -> dict[str, Any]:
    cpdf = course_pdf_dir(course_id)
    cpdf.mkdir(parents=True, exist_ok=True)
    files = sorted([p for p in cpdf.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"], key=lambda p: p.name.lower())
    collected: list[dict[str, Any]] = []
    embedder = get_embedder()
    for pdf in files:
        try:
            reader = PdfReader(str(pdf))
        except Exception:
            continue
        chunks_raw: list[tuple[int, str]] = []
        for page_idx, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            for chunk in split_text_chunks(txt):
                chunks_raw.append((page_idx + 1, chunk))
        if not chunks_raw:
            continue
        embeds = list(embedder.embed([c[1] for c in chunks_raw]))
        for i, (page_num, txt) in enumerate(chunks_raw):
            collected.append(
                {
                    "source": pdf.name,
                    "page": page_num,
                    "text": txt,
                    "embedding": [float(x) for x in np.array(embeds[i], dtype=np.float32).tolist()],
                }
            )
    idx_file = course_index_file(course_id)
    idx_file.parent.mkdir(parents=True, exist_ok=True)
    idx_file.write_text(
        json.dumps(
            {
                "updatedAt": now_ms(),
                "courseId": course_id,
                "files": [p.name for p in files],
                "chunks": collected,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    course_rag_cache.pop(course_id, None)
    load_course_index(course_id)
    return {"fileCount": len(files), "chunkCount": len(collected)}


async def rebuild_course_index(course_id: str) -> None:
    pdf_reindex_state[course_id] = {"running": True, "error": "", "updatedAt": now_ms()}
    await broadcast({"type": "pdf_indexing", "courseId": course_id, "running": True, "error": ""})
    try:
        stats = await asyncio.to_thread(rebuild_course_index_sync, course_id)
        pdf_reindex_state[course_id] = {"running": False, "error": "", "updatedAt": now_ms(), **stats}
        await broadcast(
            {
                "type": "pdf_indexing",
                "courseId": course_id,
                "running": False,
                "error": "",
                "fileCount": stats.get("fileCount", 0),
                "chunkCount": stats.get("chunkCount", 0),
            }
        )
    except Exception as exc:
        pdf_reindex_state[course_id] = {"running": False, "error": str(exc), "updatedAt": now_ms()}
        await broadcast({"type": "pdf_indexing", "courseId": course_id, "running": False, "error": str(exc)})


def chat_supervision_payload() -> dict[str, Any]:
    queue_items = [
        {
            "sessionId": sid,
            "name": chat_sessions.get(sid, {}).get("studentName", "Étudiant"),
            "position": idx + 1,
        }
        for idx, sid in enumerate(chat_queue)
    ]
    active_items = [
        {
            "sessionId": sid,
            "name": chat_sessions.get(sid, {}).get("studentName", "Étudiant"),
        }
        for sid in sorted(chat_active)
    ]
    return {
        "queueLength": len(chat_queue),
        "activeCount": len(chat_active),
        "queue": queue_items,
        "active": active_items,
        "promptsSession": int(chat_prompts_session),
        "promptsTotal": int(state.get("metrics", {}).get("promptsTotal", 0)),
    }


def chat_session_payload(session_id: str) -> dict[str, Any]:
    position = chat_queue.index(session_id) + 1 if session_id in chat_queue else 0
    return {
        "sessionId": session_id,
        "active": session_id in chat_active,
        "position": position,
        "queueLength": len(chat_queue),
    }


async def acquire_chat_slot(session_id: str) -> None:
    async with chat_cond:
        if session_id in chat_active:
            return
        if session_id not in chat_queue:
            chat_queue.append(session_id)
        while True:
            can_take = len(chat_active) < CHAT_MAX_CONCURRENCY and chat_queue and chat_queue[0] == session_id
            if can_take:
                chat_queue.pop(0)
                chat_active.add(session_id)
                break
            await chat_cond.wait()
    await broadcast({"type": "chat_supervision", "data": chat_supervision_payload()})
    await broadcast_users()


async def release_chat_slot(session_id: str, clear_history: bool = True) -> None:
    global chat_queue
    async with chat_cond:
        if session_id in chat_active:
            chat_active.remove(session_id)
        if session_id in chat_queue:
            chat_queue = [sid for sid in chat_queue if sid != session_id]
        session = chat_sessions.get(session_id)
        if session:
            if clear_history:
                session["history"] = []
            session["lastActivity"] = now_ms()
        chat_cond.notify_all()
    await broadcast({"type": "chat_supervision", "data": chat_supervision_payload()})
    await broadcast_users()


async def chat_cleanup_loop() -> None:
    while True:
        await asyncio.sleep(5)
        stale: list[str] = []
        async with chat_lock:
            now = now_ms()
            for sid in list(chat_active):
                sess = chat_sessions.get(sid, {})
                last = int(sess.get("lastActivity", 0))
                if now - last > CHAT_INACTIVITY_SECONDS * 1000:
                    stale.append(sid)
        for sid in stale:
            await release_chat_slot(sid, clear_history=True)


def build_chat_context(course_id: str, hotspot_title: str, hotspot_html: str, all_hotspots: list[dict[str, Any]], prompt: str) -> str:
    current = stripped_html(hotspot_html or "")
    all_h = []
    for h in all_hotspots or []:
        title = str(h.get("title", "Hotspot")).strip() or "Hotspot"
        body = stripped_html(str(h.get("html", "")))
        if not body:
            continue
        all_h.append(f"- {title}: {body[:500]}")
    rag_chunks = retrieve_course_rag(course_id, prompt, top_k=4)
    rag_text = []
    for c in rag_chunks:
        rag_text.append(f"- [{c.get('source','pdf')} p.{c.get('page', 0)}] {str(c.get('text', ''))[:550]}")
    return (
        f"Hotspot courant: {hotspot_title or 'Hotspot'}\n"
        f"Contenu hotspot courant:\n{current[:2200]}\n\n"
        f"Autres hotspots du whiteboard:\n{chr(10).join(all_h)[:3800]}\n\n"
        f"Extraits RAG PDF du cours:\n{chr(10).join(rag_text)[:3800]}"
    )


def run_llm_chat(messages: list[dict[str, str]]) -> str:
    cfg = current_llm_config()
    provider = cfg["provider"]
    if provider == "apertus":
        return chat_completion_apertus(messages, cfg["apertusModel"])
    llm = get_llm()
    out = llm.create_chat_completion(messages=messages, max_tokens=500, temperature=0.2)
    txt = out["choices"][0]["message"]["content"]
    return str(txt or "").strip()


def make_initial_state() -> dict[str, Any]:
    course_id = make_id("course")
    board_id = make_id("wb")
    return {
        "version": 1,
        "updatedAt": now_ms(),
        "metrics": {"promptsTotal": 0},
        "llm": default_llm_config(),
        "activeCourseId": course_id,
        "activeWhiteboardId": board_id,
        "courses": [
            {
                "id": course_id,
                "name": "Cours 1",
                "whiteboardOrder": [board_id],
                "lastWhiteboardId": board_id,
            }
        ],
        "whiteboards": {
            board_id: {
                "id": board_id,
                "courseId": course_id,
                "name": "WB 1",
                "strokes": [],
                "images": [],
                "hotspots": [],
            }
        },
    }


def load_state_from_disk() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return make_initial_state()
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return make_initial_state()
        if "courses" not in payload or "whiteboards" not in payload:
            return make_initial_state()
        if "metrics" not in payload or not isinstance(payload.get("metrics"), dict):
            payload["metrics"] = {"promptsTotal": 0}
        payload["metrics"]["promptsTotal"] = int(payload["metrics"].get("promptsTotal", 0))
        if "llm" not in payload or not isinstance(payload.get("llm"), dict):
            payload["llm"] = default_llm_config()
        payload["llm"]["provider"] = normalize_llm_provider(str(payload["llm"].get("provider", default_llm_config()["provider"])))
        payload["llm"]["apertusModel"] = str(payload["llm"].get("apertusModel", APERTUS_MODEL) or APERTUS_MODEL).strip()
        return payload
    except Exception:
        return make_initial_state()


def save_state_to_disk() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def get_course(course_id: str) -> dict[str, Any]:
    for c in state["courses"]:
        if c["id"] == course_id:
            return c
    raise HTTPException(404, "Course not found")


def get_whiteboard(board_id: str) -> dict[str, Any]:
    b = state["whiteboards"].get(board_id)
    if not b:
        raise HTTPException(404, "Whiteboard not found")
    return b


def ensure_active_consistency() -> None:
    if not state["courses"]:
        fresh = make_initial_state()
        state.clear()
        state.update(fresh)
        return
    all_courses = {c["id"] for c in state["courses"]}
    if state.get("activeCourseId") not in all_courses:
        state["activeCourseId"] = state["courses"][0]["id"]
    active_course = get_course(state["activeCourseId"])
    order = [wb_id for wb_id in active_course.get("whiteboardOrder", []) if wb_id in state["whiteboards"]]
    if not order:
        wb_id = make_id("wb")
        state["whiteboards"][wb_id] = {
            "id": wb_id,
            "courseId": active_course["id"],
            "name": "WB 1",
            "strokes": [],
            "images": [],
            "hotspots": [],
        }
        active_course["whiteboardOrder"] = [wb_id]
        active_course["lastWhiteboardId"] = wb_id
        order = [wb_id]
    active_wb = state.get("activeWhiteboardId")
    if active_wb not in order:
        pick = active_course.get("lastWhiteboardId")
        if pick in order:
            state["activeWhiteboardId"] = pick
        else:
            state["activeWhiteboardId"] = order[0]
    active_course["lastWhiteboardId"] = state["activeWhiteboardId"]


def touch_and_save() -> None:
    state["updatedAt"] = now_ms()
    ensure_active_consistency()
    save_state_to_disk()


def stripped_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def board_summary(board: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": board["id"],
        "courseId": board["courseId"],
        "name": board["name"],
        "strokeCount": len(board.get("strokes", [])),
        "imageCount": len(board.get("images", [])),
        "hotspotCount": len(board.get("hotspots", [])),
    }


def whiteboard_export_payload(whiteboard_id: str) -> dict[str, Any]:
    wb = get_whiteboard(whiteboard_id)
    course = get_course(wb["courseId"])
    return {
        "format": "maxboard.whiteboard.v1",
        "exportedAt": now_ms(),
        "source": {
            "courseId": course["id"],
            "courseName": course["name"],
            "whiteboardId": wb["id"],
            "whiteboardName": wb["name"],
        },
        "whiteboard": {
            "name": wb["name"],
            "strokes": copy.deepcopy(wb.get("strokes", [])),
            "images": copy.deepcopy(wb.get("images", [])),
            "hotspots": copy.deepcopy(wb.get("hotspots", [])),
        },
    }


def public_state() -> dict[str, Any]:
    boards = {
        bid: board_summary(b)
        for bid, b in state["whiteboards"].items()
    }
    return {
        "updatedAt": state["updatedAt"],
        "activeCourseId": state["activeCourseId"],
        "activeWhiteboardId": state["activeWhiteboardId"],
        "courses": copy.deepcopy(state["courses"]),
        "whiteboards": boards,
    }


def active_board_payload() -> dict[str, Any]:
    wb = get_whiteboard(state["activeWhiteboardId"])
    return {
        "id": wb["id"],
        "courseId": wb["courseId"],
        "name": wb["name"],
        "strokes": wb.get("strokes", []),
        "images": wb.get("images", []),
        "hotspots": wb.get("hotspots", []),
    }


async def send_json(ws: WebSocket, payload: dict[str, Any]) -> None:
    try:
        await ws.send_text(json.dumps(payload))
    except Exception:
        pass


async def broadcast(payload: dict[str, Any], exclude: Optional[WebSocket] = None) -> None:
    async with clients_lock:
        targets = [ws for ws in clients if ws is not exclude]
    if not targets:
        return
    text = json.dumps(payload)
    for ws in list(targets):
        try:
            await ws.send_text(text)
        except Exception:
            pass


async def broadcast_users() -> None:
    async with clients_lock:
        count = len(clients)
        students = sum(1 for ws in clients if client_roles.get(id(ws), "student") == "student")
    await broadcast(
        {
            "type": "users",
            "count": count,
            "students": students,
            "queue": len(chat_queue),
            "promptsSession": int(chat_prompts_session),
        }
    )


async def broadcast_catalog_and_active() -> None:
    await broadcast(
        {
            "type": "catalog",
            "state": public_state(),
            "activeBoard": active_board_payload(),
        }
    )


@app.on_event("startup")
async def startup() -> None:
    global state
    state = load_state_from_disk()
    COURSES_DIR.mkdir(parents=True, exist_ok=True)
    ensure_active_consistency()
    touch_and_save()
    asyncio.create_task(chat_cleanup_loop())


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/bootstrap")
async def api_bootstrap() -> dict[str, Any]:
    host = detect_local_ip()
    course_id = state.get("activeCourseId", "")
    llm_cfg = current_llm_config()
    return {
        "state": public_state(),
        "activeBoard": active_board_payload(),
        "shareBaseUrl": f"http://{host}:{PORT}",
        "pdfIndexing": pdf_reindex_state.get(course_id, {"running": False, "error": "", "updatedAt": 0}),
        "chatSupervision": chat_supervision_payload(),
        "llmProvider": llm_cfg["provider"],
        "llmConfig": llm_cfg,
    }


@app.post("/api/courses")
async def create_course(body: CreateCourseBody) -> dict[str, Any]:
    async with state_lock:
        cid = make_id("course")
        wid = make_id("wb")
        state["courses"].append(
            {
                "id": cid,
                "name": sanitize_name(body.name, "Nouveau cours"),
                "whiteboardOrder": [wid],
                "lastWhiteboardId": wid,
            }
        )
        state["whiteboards"][wid] = {
            "id": wid,
            "courseId": cid,
            "name": "WB 1",
            "strokes": [],
            "images": [],
            "hotspots": [],
        }
        state["activeCourseId"] = cid
        state["activeWhiteboardId"] = wid
        course_pdf_dir(cid).mkdir(parents=True, exist_ok=True)
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.patch("/api/courses/{course_id}")
async def rename_course(course_id: str, body: RenameBody) -> dict[str, Any]:
    async with state_lock:
        c = get_course(course_id)
        c["name"] = sanitize_name(body.name, c["name"])
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/courses/{course_id}/duplicate")
async def duplicate_course(course_id: str) -> dict[str, Any]:
    async with state_lock:
        src = get_course(course_id)
        new_course_id = make_id("course")
        new_order: list[str] = []
        for old_wid in src.get("whiteboardOrder", []):
            old_wb = get_whiteboard(old_wid)
            new_wid = make_id("wb")
            copied = copy.deepcopy(old_wb)
            copied["id"] = new_wid
            copied["courseId"] = new_course_id
            state["whiteboards"][new_wid] = copied
            new_order.append(new_wid)
        if not new_order:
            new_wid = make_id("wb")
            state["whiteboards"][new_wid] = {
                "id": new_wid,
                "courseId": new_course_id,
                "name": "WB 1",
                "strokes": [],
                "images": [],
                "hotspots": [],
            }
            new_order = [new_wid]
        duplicated = {
            "id": new_course_id,
            "name": f"{src['name']} (copie)",
            "whiteboardOrder": new_order,
            "lastWhiteboardId": new_order[0],
        }
        state["courses"].append(duplicated)
        state["activeCourseId"] = duplicated["id"]
        state["activeWhiteboardId"] = duplicated["lastWhiteboardId"]
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.delete("/api/courses/{course_id}")
async def delete_course(course_id: str) -> dict[str, Any]:
    async with state_lock:
        if len(state["courses"]) <= 1:
            raise HTTPException(400, "Au moins un cours est requis")
        course = get_course(course_id)
        wb_ids = list(course.get("whiteboardOrder", []))
        state["courses"] = [c for c in state["courses"] if c["id"] != course_id]
        for wid in wb_ids:
            state["whiteboards"].pop(wid, None)
        cdir = course_dir(course_id)
        if cdir.exists():
            shutil.rmtree(cdir, ignore_errors=True)
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/courses/reorder")
async def reorder_courses(body: ReorderCoursesBody) -> dict[str, Any]:
    async with state_lock:
        ids = [c["id"] for c in state["courses"]]
        if sorted(ids) != sorted(body.courseIds):
            raise HTTPException(400, "Liste de cours invalide")
        new_map = {c["id"]: c for c in state["courses"]}
        state["courses"] = [new_map[cid] for cid in body.courseIds]
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/courses/{course_id}/activate")
async def activate_course(course_id: str) -> dict[str, Any]:
    async with state_lock:
        c = get_course(course_id)
        state["activeCourseId"] = c["id"]
        order = [wid for wid in c.get("whiteboardOrder", []) if wid in state["whiteboards"]]
        if not order:
            raise HTTPException(400, "Ce cours ne contient pas de whiteboard")
        pick = c.get("lastWhiteboardId")
        state["activeWhiteboardId"] = pick if pick in order else order[0]
        c["lastWhiteboardId"] = state["activeWhiteboardId"]
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/courses/{course_id}/whiteboards")
async def create_whiteboard(course_id: str, body: CreateWhiteboardBody) -> dict[str, Any]:
    async with state_lock:
        c = get_course(course_id)
        wid = make_id("wb")
        state["whiteboards"][wid] = {
            "id": wid,
            "courseId": c["id"],
            "name": sanitize_name(body.name, "Nouveau whiteboard"),
            "strokes": [],
            "images": [],
            "hotspots": [],
        }
        c.setdefault("whiteboardOrder", []).append(wid)
        c["lastWhiteboardId"] = wid
        state["activeCourseId"] = c["id"]
        state["activeWhiteboardId"] = wid
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.patch("/api/whiteboards/{whiteboard_id}")
async def rename_whiteboard(whiteboard_id: str, body: RenameBody) -> dict[str, Any]:
    async with state_lock:
        wb = get_whiteboard(whiteboard_id)
        wb["name"] = sanitize_name(body.name, wb["name"])
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/whiteboards/{whiteboard_id}/duplicate")
async def duplicate_whiteboard(whiteboard_id: str, body: DuplicateWhiteboardBody) -> dict[str, Any]:
    async with state_lock:
        src = get_whiteboard(whiteboard_id)
        target_course_id = body.targetCourseId or src["courseId"]
        course = get_course(target_course_id)
        new_wid = make_id("wb")
        cloned = copy.deepcopy(src)
        cloned["id"] = new_wid
        cloned["courseId"] = target_course_id
        cloned["name"] = f"{src['name']} (copie)"
        state["whiteboards"][new_wid] = cloned
        course.setdefault("whiteboardOrder", []).append(new_wid)
        course["lastWhiteboardId"] = new_wid
        state["activeCourseId"] = target_course_id
        state["activeWhiteboardId"] = new_wid
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.get("/api/whiteboards/{whiteboard_id}/export")
async def export_whiteboard(whiteboard_id: str) -> Response:
    async with state_lock:
        payload = whiteboard_export_payload(whiteboard_id)
        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", payload["source"]["whiteboardName"] or "whiteboard")
    content = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.maxboard.json"'},
    )


@app.post("/api/whiteboards/import")
async def import_whiteboard(body: ImportWhiteboardBody) -> dict[str, Any]:
    async with state_lock:
        payload = body.payload if isinstance(body.payload, dict) else {}
        if payload.get("format") != "maxboard.whiteboard.v1":
            raise HTTPException(400, "Format d'import non supporté")
        whiteboard = payload.get("whiteboard")
        if not isinstance(whiteboard, dict):
            raise HTTPException(400, "Payload whiteboard invalide")

        target_course_id = body.targetCourseId or state.get("activeCourseId")
        course = get_course(str(target_course_id))

        imported_name = sanitize_name(str(body.name or whiteboard.get("name") or "Whiteboard importé"), "Whiteboard importé")
        strokes = whiteboard.get("strokes", [])
        images = whiteboard.get("images", [])
        hotspots = whiteboard.get("hotspots", [])
        if not isinstance(strokes, list) or not isinstance(images, list) or not isinstance(hotspots, list):
            raise HTTPException(400, "Payload strokes/images/hotspots invalide")

        wid = make_id("wb")
        state["whiteboards"][wid] = {
            "id": wid,
            "courseId": course["id"],
            "name": imported_name,
            "strokes": copy.deepcopy(strokes),
            "images": copy.deepcopy(images),
            "hotspots": copy.deepcopy(hotspots),
        }
        course.setdefault("whiteboardOrder", []).append(wid)
        course["lastWhiteboardId"] = wid
        state["activeCourseId"] = course["id"]
        state["activeWhiteboardId"] = wid
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True, "whiteboardId": wid}


@app.delete("/api/whiteboards/{whiteboard_id}")
async def delete_whiteboard(whiteboard_id: str) -> dict[str, Any]:
    async with state_lock:
        wb = get_whiteboard(whiteboard_id)
        course = get_course(wb["courseId"])
        if len(course.get("whiteboardOrder", [])) <= 1:
            raise HTTPException(400, "Un cours doit contenir au moins un whiteboard")
        course["whiteboardOrder"] = [wid for wid in course["whiteboardOrder"] if wid != whiteboard_id]
        if course.get("lastWhiteboardId") == whiteboard_id:
            course["lastWhiteboardId"] = course["whiteboardOrder"][0]
        state["whiteboards"].pop(whiteboard_id, None)
        if state.get("activeWhiteboardId") == whiteboard_id:
            state["activeCourseId"] = course["id"]
            state["activeWhiteboardId"] = course["lastWhiteboardId"]
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/courses/{course_id}/whiteboards/reorder")
async def reorder_whiteboards(course_id: str, body: ReorderWhiteboardsBody) -> dict[str, Any]:
    async with state_lock:
        course = get_course(course_id)
        current_ids = list(course.get("whiteboardOrder", []))
        if sorted(current_ids) != sorted(body.whiteboardIds):
            raise HTTPException(400, "Liste de whiteboards invalide")
        course["whiteboardOrder"] = list(body.whiteboardIds)
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.post("/api/whiteboards/activate")
async def activate_whiteboard(body: ActivateWhiteboardBody) -> dict[str, Any]:
    async with state_lock:
        wb = get_whiteboard(body.whiteboardId)
        course = get_course(wb["courseId"])
        state["activeCourseId"] = wb["courseId"]
        state["activeWhiteboardId"] = wb["id"]
        course["lastWhiteboardId"] = wb["id"]
        touch_and_save()
    await broadcast_catalog_and_active()
    return {"ok": True}


@app.get("/api/courses/{course_id}/pdfs")
async def list_course_pdfs(course_id: str) -> dict[str, Any]:
    async with state_lock:
        course = get_course(course_id)
        cpdf = course_pdf_dir(course["id"])
        cpdf.mkdir(parents=True, exist_ok=True)
        files = sorted([p for p in cpdf.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"], key=lambda p: p.name.lower())
        rows = []
        for p in files:
            st = p.stat()
            rows.append({"name": p.name, "size": int(st.st_size), "updatedAt": int(st.st_mtime * 1000)})
        status = pdf_reindex_state.get(course["id"], {"running": False, "error": "", "updatedAt": 0})
    return {"courseId": course_id, "files": rows, "indexing": status}


@app.post("/api/courses/{course_id}/pdfs/upload")
async def upload_course_pdf(course_id: str, file: UploadFile = File(...)) -> dict[str, Any]:
    async with state_lock:
        course = get_course(course_id)
        cpdf = course_pdf_dir(course["id"])
        cpdf.mkdir(parents=True, exist_ok=True)
        files = [p for p in cpdf.iterdir() if p.is_file() and p.suffix.lower() == ".pdf"]
        if len(files) >= PDF_MAX_FILES_PER_COURSE:
            raise HTTPException(400, f"Maximum {PDF_MAX_FILES_PER_COURSE} PDFs par cours")
        name = sanitize_filename(file.filename or "document.pdf")
        target = cpdf / name
        blob = await file.read()
        if len(blob) > PDF_MAX_SIZE_BYTES:
            raise HTTPException(400, f"PDF trop volumineux (max {PDF_MAX_SIZE_BYTES // (1024 * 1024)} MB)")
        target.write_bytes(blob)
    asyncio.create_task(rebuild_course_index(course_id))
    return {"ok": True, "name": name}


@app.patch("/api/courses/{course_id}/pdfs/{pdf_name}")
async def rename_course_pdf(course_id: str, pdf_name: str, body: RenamePdfBody) -> dict[str, Any]:
    async with state_lock:
        course = get_course(course_id)
        cpdf = course_pdf_dir(course["id"])
        src = cpdf / sanitize_filename(pdf_name)
        if not src.exists():
            raise HTTPException(404, "PDF introuvable")
        dst = cpdf / sanitize_filename(body.newName)
        if dst.exists():
            raise HTTPException(400, "Un PDF avec ce nom existe déjà")
        src.rename(dst)
    asyncio.create_task(rebuild_course_index(course_id))
    return {"ok": True}


@app.delete("/api/courses/{course_id}/pdfs/{pdf_name}")
async def delete_course_pdf(course_id: str, pdf_name: str) -> dict[str, Any]:
    async with state_lock:
        course = get_course(course_id)
        cpdf = course_pdf_dir(course["id"])
        target = cpdf / sanitize_filename(pdf_name)
        if not target.exists():
            raise HTTPException(404, "PDF introuvable")
        target.unlink()
    asyncio.create_task(rebuild_course_index(course_id))
    return {"ok": True}


@app.get("/api/qr")
async def api_qr(url: str = Query(..., min_length=3, max_length=2000)) -> Response:
    img = qrcode.make(url)
    bio = BytesIO()
    img.save(bio, format="PNG")
    return Response(content=bio.getvalue(), media_type="image/png")


@app.post("/api/export/pdf")
async def export_pdf(body: ExportPdfBody) -> Response:
    if "," not in body.imageDataUrl:
        raise HTTPException(400, "imageDataUrl invalide")
    try:
        raw = body.imageDataUrl.split(",", 1)[1]
        import base64
        image_bytes = base64.b64decode(raw)
    except Exception:
        raise HTTPException(400, "Impossible de decoder l'image")

    output = BytesIO()
    pdf = pdf_canvas.Canvas(output, pagesize=A4)
    width, height = A4

    title = f"{body.courseName} - {body.whiteboardName}".strip(" -")
    pdf.setTitle(title or "MaxBoard export")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(36, height - 40, title or "MaxBoard")

    img = ImageReader(BytesIO(image_bytes))
    img_w, img_h = img.getSize()
    max_w = width - 72
    max_h = height - 120
    ratio = min(max_w / max(1, img_w), max_h / max(1, img_h))
    draw_w = img_w * ratio
    draw_h = img_h * ratio
    x = (width - draw_w) / 2
    y = height - 80 - draw_h
    pdf.drawImage(img, x, y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
    pdf.setFont("Helvetica", 9)
    pdf.drawString(36, 24, f"Exporte le {time.strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.showPage()

    ordered = sorted(
        [{"title": h.title.strip() or "Hotspot", "content": stripped_html(h.html)} for h in body.hotspots],
        key=lambda h: h["title"].lower(),
    )
    if not ordered:
        ordered = [{"title": "Aucun hotspot", "content": "Ce whiteboard ne contient pas de hotspot."}]

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(36, height - 40, "Hotspots (ordre alphabetique)")
    y = height - 70
    for i, h in enumerate(ordered, start=1):
        text = f"{i}. {h['title']}"
        pdf.setFont("Helvetica-Bold", 11)
        if y < 120:
            pdf.showPage()
            y = height - 40
        pdf.drawString(36, y, text)
        y -= 16

        content = h["content"] or "(contenu vide)"
        words = content.split()
        line = ""
        pdf.setFont("Helvetica", 10)
        for w in words:
            candidate = (line + " " + w).strip()
            if pdf.stringWidth(candidate, "Helvetica", 10) <= (width - 72):
                line = candidate
            else:
                if y < 70:
                    pdf.showPage()
                    y = height - 40
                    pdf.setFont("Helvetica", 10)
                pdf.drawString(46, y, line)
                y -= 13
                line = w
        if line:
            if y < 70:
                pdf.showPage()
                y = height - 40
                pdf.setFont("Helvetica", 10)
            pdf.drawString(46, y, line)
            y -= 18

    pdf.save()
    data = output.getvalue()
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", body.whiteboardName or "whiteboard")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}.pdf"'},
    )


@app.get("/api/chat/queue/{session_id}")
async def chat_queue_status(session_id: str) -> dict[str, Any]:
    async with chat_lock:
        return {
            **chat_session_payload(session_id),
            "supervision": chat_supervision_payload(),
        }


@app.get("/api/chat/supervision")
async def chat_supervision() -> dict[str, Any]:
    async with chat_lock:
        return chat_supervision_payload()


@app.get("/api/llm/config")
async def llm_config_get() -> dict[str, Any]:
    async with state_lock:
        return {"config": current_llm_config()}


@app.post("/api/llm/config")
async def llm_config_set(body: LlmConfigBody) -> dict[str, Any]:
    async with state_lock:
        state.setdefault("llm", {})
        state["llm"]["provider"] = normalize_llm_provider(body.provider)
        next_model = str(body.apertusModel or APERTUS_MODEL).strip() or APERTUS_MODEL
        state["llm"]["apertusModel"] = next_model
        touch_and_save()
        cfg = current_llm_config()
    await broadcast({"type": "llm_config", "config": cfg})
    return {"ok": True, "config": cfg}


@app.post("/api/chat/release")
async def chat_release(body: ChatReleaseBody) -> dict[str, Any]:
    await release_chat_slot(body.sessionId, clear_history=True)
    return {"ok": True}


@app.post("/api/chat/hotspot")
async def chat_hotspot(body: ChatAskBody) -> dict[str, Any]:
    global chat_prompts_session
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt vide")

    session_id = str(body.sessionId or "").strip()
    if not session_id:
        raise HTTPException(400, "sessionId requis")
    name = sanitize_name(body.studentName, "Étudiant")
    async with chat_lock:
        sess = chat_sessions.setdefault(
            session_id,
            {
                "studentName": name,
                "history": [],
                "lastActivity": now_ms(),
                "courseId": body.courseId,
                "whiteboardId": body.whiteboardId,
                "hotspotId": body.hotspotId,
            },
        )
        sess["studentName"] = name
        sess["courseId"] = body.courseId
        sess["whiteboardId"] = body.whiteboardId
        sess["hotspotId"] = body.hotspotId
        sess["lastActivity"] = now_ms()

    await acquire_chat_slot(session_id)

    try:
        context = build_chat_context(
            course_id=body.courseId,
            hotspot_title=body.hotspotTitle,
            hotspot_html=body.hotspotHtml,
            all_hotspots=body.allHotspots or [],
            prompt=prompt,
        )
        async with chat_lock:
            sess = chat_sessions[session_id]
            history = list(sess.get("history", []))[-8:]
            sess["history"] = history
            chat_prompts_session += 1
        async with state_lock:
            state.setdefault("metrics", {})
            state["metrics"]["promptsTotal"] = int(state["metrics"].get("promptsTotal", 0)) + 1
            touch_and_save()
        messages = [
            {
                "role": "system",
                "content": (
                    "Tu es un assistant pédagogique concis. Réponds en français. "
                    "Appuie-toi d'abord sur le hotspot courant, puis sur les autres hotspots, puis sur les extraits PDF RAG. "
                    "Si une info manque, dis-le clairement."
                ),
            },
            {"role": "system", "content": context[:9000]},
        ]
        for item in history:
            role = item.get("role")
            content = str(item.get("content", ""))
            if role in {"user", "assistant"} and content:
                messages.append({"role": role, "content": content[:2000]})
        messages.append({"role": "user", "content": prompt[:2000]})
        answer = await asyncio.to_thread(run_llm_chat, messages)
        async with chat_lock:
            sess = chat_sessions.get(session_id, {})
            h = list(sess.get("history", []))
            h.append({"role": "user", "content": prompt})
            h.append({"role": "assistant", "content": answer})
            sess["history"] = h[-10:]
            sess["lastActivity"] = now_ms()
        await broadcast({"type": "chat_supervision", "data": chat_supervision_payload()})
        await broadcast_users()
        return {
            "ok": True,
            "answer": answer,
            "session": chat_session_payload(session_id),
            "supervision": chat_supervision_payload(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Erreur chat: {exc}")


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, role: str = "student") -> None:
    await websocket.accept()
    async with clients_lock:
        clients.append(websocket)
        client_roles[id(websocket)] = role
        users_count = len(clients)
        students_count = sum(1 for ws in clients if client_roles.get(id(ws), "student") == "student")

    await send_json(
        websocket,
        {
            "type": "init",
            "role": role,
            "state": public_state(),
            "activeBoard": active_board_payload(),
            "users": users_count,
            "students": students_count,
            "pdfIndexing": pdf_reindex_state.get(state.get("activeCourseId", ""), {"running": False, "error": "", "updatedAt": 0}),
            "chatSupervision": chat_supervision_payload(),
        },
    )
    await broadcast_users()

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            mtype = str(msg.get("type", ""))

            async with state_lock:
                active_wb = get_whiteboard(state["activeWhiteboardId"])
                dirty = False

                if mtype == "stroke":
                    stroke = msg.get("stroke")
                    if stroke:
                        active_wb.setdefault("strokes", []).append(stroke)
                        dirty = True
                elif mtype == "clear":
                    active_wb["strokes"] = []
                    active_wb["images"] = []
                    dirty = True
                elif mtype == "image_add":
                    item = msg.get("image")
                    if item:
                        active_wb.setdefault("images", []).append(item)
                        dirty = True
                elif mtype == "image_update":
                    iid = msg.get("id")
                    for it in active_wb.get("images", []):
                        if it.get("id") == iid:
                            it["x"] = msg.get("x", it.get("x", 0))
                            it["y"] = msg.get("y", it.get("y", 0))
                            it["w"] = msg.get("w", it.get("w", 0.2))
                            it["h"] = msg.get("h", it.get("h", 0.2))
                            dirty = True
                            break
                elif mtype == "image_delete":
                    iid = msg.get("id")
                    before = len(active_wb.get("images", []))
                    active_wb["images"] = [i for i in active_wb.get("images", []) if i.get("id") != iid]
                    dirty = len(active_wb["images"]) != before
                elif mtype == "hotspot_upsert":
                    hs = msg.get("hotspot")
                    if hs:
                        hs_id = hs.get("id") or make_id("hs")
                        hs["id"] = hs_id
                        found = False
                        for idx, item in enumerate(active_wb.get("hotspots", [])):
                            if item.get("id") == hs_id:
                                active_wb["hotspots"][idx] = hs
                                found = True
                                break
                        if not found:
                            active_wb.setdefault("hotspots", []).append(hs)
                        dirty = True
                elif mtype == "hotspot_delete":
                    hs_id = msg.get("id")
                    before = len(active_wb.get("hotspots", []))
                    active_wb["hotspots"] = [h for h in active_wb.get("hotspots", []) if h.get("id") != hs_id]
                    dirty = len(active_wb["hotspots"]) != before
                elif mtype == "activate_whiteboard":
                    wb_id = str(msg.get("whiteboardId", ""))
                    wb = get_whiteboard(wb_id)
                    c = get_course(wb["courseId"])
                    state["activeCourseId"] = c["id"]
                    state["activeWhiteboardId"] = wb["id"]
                    c["lastWhiteboardId"] = wb["id"]
                    dirty = True
                elif mtype == "undo_stroke":
                    if active_wb.get("strokes"):
                        active_wb["strokes"].pop()
                        dirty = True

                if dirty:
                    touch_and_save()

            if mtype == "activate_whiteboard":
                await broadcast_catalog_and_active()
            elif mtype in {
                "stroke",
                "clear",
                "image_add",
                "image_update",
                "image_delete",
                "hotspot_upsert",
                "hotspot_delete",
                "undo_stroke",
            }:
                if mtype == "clear":
                    await broadcast({"type": "clear"})
                elif mtype == "undo_stroke":
                    await broadcast({"type": "active_board_sync", "board": active_board_payload()})
                else:
                    await broadcast(msg)
    except WebSocketDisconnect:
        pass
    finally:
        async with clients_lock:
            if websocket in clients:
                clients.remove(websocket)
            client_roles.pop(id(websocket), None)
        await broadcast_users()


app.mount("/assets", StaticFiles(directory=str(WEB_DIR / "assets")), name="assets")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
