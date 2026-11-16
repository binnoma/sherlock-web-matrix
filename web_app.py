import os
import sys
import asyncio
import json
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

from update_database import update_database, OUTPUT_FILE as EXPANDED_DB_FILE
from osint_recon import recon_email, recon_phone, recon_username, get_site_favicon
from database_history import save_scan, get_all_scans, get_scan, delete_scan

app = FastAPI(title="Sherlock OSINT Cyber Matrix")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

SOCIAL_PLATFORMS = [
    "Twitter", "Instagram", "TikTok", "Reddit", "Telegram", 
    "YouTube", "Pinterest", "Snapchat", "threads", "tumblr", 
    "Twitch", "Medium", "Spotify"
]

def get_db_stats():
    expanded_count = 0
    if EXPANDED_DB_FILE.exists():
        try:
            with open(EXPANDED_DB_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                expanded_count = len(d) - 1
        except Exception:
            pass
    return {
        "official_sites": 482,
        "expanded_sites": expanded_count or 3025,
        "social_sites": len(SOCIAL_PLATFORMS),
        "has_expanded": EXPANDED_DB_FILE.exists()
    }

@app.get("/", response_class=HTMLResponse)
async def index():
    index_file = TEMPLATES_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>ملف الواجهة templates/index.html غير موجود</h1>", status_code=404)

@app.get("/api/db_stats")
async def db_stats_endpoint():
    return JSONResponse(get_db_stats())

@app.post("/api/update_database")
async def trigger_update_db():
    loop = asyncio.get_event_loop()
    try:
        new_count = await loop.run_in_executor(None, update_database)
        return JSONResponse({"status": "success", "total_sites": new_count, "message": f"تم تحديث ودمج {new_count} موقعاً بنجاح من GitHub"})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

# Deep Recon Endpoints
@app.get("/api/recon/username")
async def api_recon_username(username: str = Query(..., description="Target username")):
    return JSONResponse(recon_username(username))

@app.get("/api/recon/email")
async def api_recon_email(email: str = Query(..., description="Target email")):
    return JSONResponse(recon_email(email))

@app.get("/api/recon/phone")
async def api_recon_phone(phone: str = Query(..., description="Target phone"), prefix: str = Query("+971")):
    return JSONResponse(recon_phone(phone, default_prefix=prefix))

# History Endpoints
@app.get("/api/history")
async def api_get_history(limit: int = 50):
    return JSONResponse(get_all_scans(limit=limit))

@app.get("/api/history/{scan_id}")
async def api_get_scan_details(scan_id: int):
    scan = get_scan(scan_id)
    if not scan:
        return JSONResponse({"error": "Scan not found"}, status_code=404)
    return JSONResponse(scan)

@app.delete("/api/history/{scan_id}")
async def api_delete_scan(scan_id: int):
    deleted = delete_scan(scan_id)
    return JSONResponse({"success": deleted})

@app.websocket("/ws/scan")
async def websocket_scan(websocket: WebSocket):
    await websocket.accept()
    current_process = None
    runner_task = None
    stop_requested = False

    async def run_sherlock_subcommand(cmd, category="general", phase=1, seen_sites=None, collected_results=None):
        nonlocal current_process, stop_requested
        if stop_requested:
            return

        current_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        try:
            while True:
                line_bytes = await current_process.stdout.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                await websocket.send_text(json.dumps({"type": "log", "message": line, "phase": phase}))

                if line.startswith("[+]"):
                    try:
                        content = line[3:].strip()
                        if ": " in content:
                            site, url = content.split(": ", 1)
                            site = site.strip()
                            url = url.strip()

                            if seen_sites is not None:
                                if site.lower() in seen_sites:
                                    continue
                                seen_sites.add(site.lower())

                            favicon = get_site_favicon(url)
                            hit_data = {
                                "site": site,
                                "url": url,
                                "favicon": favicon,
                                "category": category,
                                "phase": phase
                            }

                            if collected_results is not None:
                                collected_results.append(hit_data)

                            await websocket.send_text(json.dumps({
                                "type": "found",
                                **hit_data
                            }))
                    except Exception:
                        pass
            await current_process.wait()
        except asyncio.CancelledError:
            if current_process and current_process.returncode is None:
                try:
                    current_process.kill()
                except Exception:
                    pass
            raise

    async def execute_investigation_pipeline(username, scope, nsfw, meta):
        nonlocal stop_requested
        seen_sites = set()
        collected_results = []
        target_display = meta.get("display", username)
        target_type = meta.get("type", "username")

        # 1. Trigger Deep Recon (Username, Email, Phone)
        try:
            if target_type == "email":
                email_recon_data = recon_email(target_display)
                await websocket.send_text(json.dumps({
                    "type": "deep_recon",
                    "recon_type": "email",
                    "data": email_recon_data
                }))
            elif target_type == "phone":
                phone_recon_data = recon_phone(target_display)
                await websocket.send_text(json.dumps({
                    "type": "deep_recon",
                    "recon_type": "phone",
                    "data": phone_recon_data
                }))
            else:
                user_recon_data = recon_username(username)
                await websocket.send_text(json.dumps({
                    "type": "deep_recon",
                    "recon_type": "username",
                    "data": user_recon_data
                }))
        except Exception as e:
            pass

        try:
            if scope == "phased":
                # PHASE 1: Priority Social Media
                await websocket.send_text(json.dumps({
                    "type": "phase_start",
                    "phase": 1,
                    "name": "social",
                    "title": "المرحلة الأولى: فحص شبكات التواصل الاجتماعي (Social Media First)",
                    "total": len(SOCIAL_PLATFORMS)
                }))

                cmd_p1 = [
                    sys.executable, "-m", "sherlock_project",
                    "--no-color", "--print-found", "--local"
                ]
                if nsfw:
                    cmd_p1.append("--nsfw")
                for s in SOCIAL_PLATFORMS:
                    cmd_p1.extend(["--site", s])
                cmd_p1.append(username)

                await run_sherlock_subcommand(cmd_p1, category="social", phase=1, seen_sites=seen_sites, collected_results=collected_results)

                if stop_requested:
                    return

                # PHASE 2: Deep Comprehensive Matrix Scan
                stats = get_db_stats()
                total_phase2 = stats["expanded_sites"] if EXPANDED_DB_FILE.exists() else stats["official_sites"]

                await websocket.send_text(json.dumps({
                    "type": "phase_start",
                    "phase": 2,
                    "name": "deep",
                    "title": f"المرحلة الثانية: جاري الفحص الشامل الموسع ({total_phase2:,} موقع)",
                    "total": total_phase2
                }))

                cmd_p2 = [
                    sys.executable, "-m", "sherlock_project",
                    "--no-color", "--print-found"
                ]
                if nsfw:
                    cmd_p2.append("--nsfw")

                if EXPANDED_DB_FILE.exists():
                    cmd_p2.extend(["--json", str(EXPANDED_DB_FILE), "--ignore-exclusions"])
                else:
                    cmd_p2.append("--local")

                cmd_p2.append(username)

                await run_sherlock_subcommand(cmd_p2, category="general", phase=2, seen_sites=seen_sites, collected_results=collected_results)

                # Save scan to database
                scan_id = save_scan(target=target_display, target_type=target_type, results=collected_results)

                await websocket.send_text(json.dumps({
                    "type": "done",
                    "scan_id": scan_id,
                    "message": f"اكتمل الفحص بنجاح للمستهدف ({target_display})"
                }))

            elif scope == "social_only":
                await websocket.send_text(json.dumps({
                    "type": "phase_start",
                    "phase": 1,
                    "name": "social",
                    "title": "فحص شبكات التواصل الاجتماعي فقط",
                    "total": len(SOCIAL_PLATFORMS)
                }))
                cmd = [
                    sys.executable, "-m", "sherlock_project",
                    "--no-color", "--print-found", "--local"
                ]
                if nsfw:
                    cmd.append("--nsfw")
                for s in SOCIAL_PLATFORMS:
                    cmd.extend(["--site", s])
                cmd.append(username)
                await run_sherlock_subcommand(cmd, category="social", phase=1, seen_sites=seen_sites, collected_results=collected_results)

                scan_id = save_scan(target=target_display, target_type=target_type, results=collected_results)

                await websocket.send_text(json.dumps({
                    "type": "done",
                    "scan_id": scan_id,
                    "message": f"اكتمل فحص شبكات التواصل للمستهدف ({target_display})"
                }))

            else:
                # Direct scan without phasing
                stats = get_db_stats()
                total_sites = stats["expanded_sites"] if (scope == "expanded" and EXPANDED_DB_FILE.exists()) else stats["official_sites"]
                await websocket.send_text(json.dumps({
                    "type": "phase_start",
                    "phase": 1,
                    "name": "deep",
                    "title": f"جاري الفحص المباشر ({total_sites:,} موقع)",
                    "total": total_sites
                }))
                cmd = [
                    sys.executable, "-m", "sherlock_project",
                    "--no-color", "--print-found"
                ]
                if nsfw:
                    cmd.append("--nsfw")
                if scope == "expanded" and EXPANDED_DB_FILE.exists():
                    cmd.extend(["--json", str(EXPANDED_DB_FILE), "--ignore-exclusions"])
                else:
                    cmd.append("--local")
                cmd.append(username)
                await run_sherlock_subcommand(cmd, category="general", phase=1, seen_sites=seen_sites, collected_results=collected_results)

                scan_id = save_scan(target=target_display, target_type=target_type, results=collected_results)

                await websocket.send_text(json.dumps({
                    "type": "done",
                    "scan_id": scan_id,
                    "message": f"اكتمل الفحص بنجاح للمستهدف ({target_display})"
                }))

        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
            except Exception:
                pass

    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            action = data.get("action")

            if action == "start":
                username = data.get("username", "").strip()
                if not username:
                    await websocket.send_text(json.dumps({"type": "error", "message": "اسم المستخدم مطلوب"}))
                    continue

                scope = data.get("scope", "phased")
                nsfw = data.get("nsfw", False)
                meta = data.get("meta", {})
                stop_requested = False

                if runner_task and not runner_task.done():
                    runner_task.cancel()

                runner_task = asyncio.create_task(execute_investigation_pipeline(username, scope, nsfw, meta))

            elif action == "stop":
                stop_requested = True
                if current_process and current_process.returncode is None:
                    try:
                        current_process.kill()
                    except Exception:
                        pass
                if runner_task and not runner_task.done():
                    runner_task.cancel()
                await websocket.send_text(json.dumps({
                    "type": "stopped",
                    "message": "تم إيقاف الفحص بناءً على طلبك"
                }))

    except WebSocketDisconnect:
        stop_requested = True
        if current_process and current_process.returncode is None:
            try:
                current_process.kill()
            except Exception:
                pass
        if runner_task and not runner_task.done():
            runner_task.cancel()
    except Exception as e:
        stop_requested = True
        if current_process and current_process.returncode is None:
            try:
                current_process.kill()
            except Exception:
                pass
        if runner_task and not runner_task.done():
            runner_task.cancel()

def start_server(host="127.0.0.1", port=8000):
    import webbrowser
    import threading
    url = f"http://{host}:{port}"
    print("=" * 60)
    print(f"[*] Sherlock Web UI Server started!")
    print(f"[*] Open in your browser: {url}")
    print("=" * 60)
    threading.Timer(1.2, webbrowser.open, [url]).start()
    uvicorn.run("web_app:app", host=host, port=port, log_level="info")

if __name__ == "__main__":
    start_server()
