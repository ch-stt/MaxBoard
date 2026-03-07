#!/usr/bin/env python3
import asyncio
import copy
import json
import re
import socket
import time
from html import unescape
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import qrcode
import uvicorn
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdf_canvas


ROOT = Path(__file__).parent
WEB_DIR = ROOT / "web"
DATA_DIR = ROOT / "data"
STATE_FILE = DATA_DIR / "state.json"
PORT = 8080


app = FastAPI(title="MaxBoard")
state_lock = asyncio.Lock()
clients_lock = asyncio.Lock()
clients: list[WebSocket] = []
state: dict[str, Any] = {}


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


def make_initial_state() -> dict[str, Any]:
    course_id = make_id("course")
    board_id = make_id("wb")
    return {
        "version": 1,
        "updatedAt": now_ms(),
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
    await broadcast({"type": "users", "count": count})


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
    ensure_active_consistency()
    touch_and_save()


@app.get("/")
async def root() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/bootstrap")
async def api_bootstrap() -> dict[str, Any]:
    host = detect_local_ip()
    return {
        "state": public_state(),
        "activeBoard": active_board_payload(),
        "shareBaseUrl": f"http://{host}:{PORT}",
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


@app.websocket("/ws/live")
async def ws_live(websocket: WebSocket, role: str = "student") -> None:
    await websocket.accept()
    async with clients_lock:
        clients.append(websocket)

    await send_json(
        websocket,
        {
            "type": "init",
            "role": role,
            "state": public_state(),
            "activeBoard": active_board_payload(),
            "users": len(clients),
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
        await broadcast_users()


app.mount("/assets", StaticFiles(directory=str(WEB_DIR / "assets")), name="assets")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
