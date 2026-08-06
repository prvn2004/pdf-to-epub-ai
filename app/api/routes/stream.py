import json
import asyncio
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from app.core.security import security_service
from app.services.session_service import session_manager

router = APIRouter(prefix="/api")

@router.get("/stream/{job_id}")
async def stream_job_events(request: Request, job_id: str):
    client_token = security_service.get_or_create_client_token(request)
    if not session_manager.verify_job_owner(job_id, client_token):
        raise HTTPException(status_code=403, detail="Unauthorized access to job stream")

    sess = session_manager.get_session(job_id)
    if not sess:
        async def err():
            yield f"event: error\ndata: {json.dumps({'msg':'Job not found'})}\n\n"
        return StreamingResponse(err(), media_type="text/event-stream")

    # Ensure queue has all historical page events for reconnecting clients
    session_manager.populate_queue_from_history(job_id)
    queue = sess["queue"]

    async def generate():
        last_idx = 0
        done_sent = False
        while True:
            while last_idx < len(queue):
                evt = queue[last_idx]
                last_idx += 1
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'])}\n\n"
                if evt["event"] in ("done", "error"):
                    done_sent = True
            if done_sent or sess.get("status") in ("done", "error"):
                if last_idx >= len(queue):
                    break
            await asyncio.sleep(0.2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
