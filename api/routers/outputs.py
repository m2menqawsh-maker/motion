"""
Outputs & Video Delivery Router (S22 - LED-065).

Canonical endpoint for video streaming and download:
- GET /projects/{project_id}/outputs/{output_id}
Supports:
- HTTP Range headers (206 Partial Content, Content-Range, Accept-Ranges)
- Seeking and streaming in HTML5 video players
- Confinement verification without leaking server filesystem paths
"""

from typing import Optional
from fastapi import APIRouter, Depends, Header, Response, status
from fastapi.responses import StreamingResponse
from api.core.auth import require_permission, Principal, Action
from api.services.output_service import OutputService

router = APIRouter()


@router.get(
    "/{project_id}/outputs/{output_id}",
    summary="Stream or download rendered video output",
)
async def get_output(
    project_id: str,
    output_id: str,
    response: Response,
    range: Optional[str] = Header(None, alias="Range"),
    principal: Principal = Depends(require_permission(Action.RENDER_READ)),
):
    """
    Delivers project output media with HTTP Range seeking support.
    """
    file_path = OutputService.get_output_path(project_id, output_id)
    total_size = file_path.stat().st_size

    # MIME type determination
    media_type = "video/mp4"
    if output_id.endswith(".webm"):
        media_type = "video/webm"
    elif output_id.endswith(".mp3"):
        media_type = "audio/mpeg"
    elif output_id.endswith(".png"):
        media_type = "image/png"

    parsed_range = OutputService.parse_range_header(range, total_size)

    if parsed_range is not None:
        start, end = parsed_range
        chunk_len = end - start + 1
        headers = {
            "Content-Range": f"bytes {start}-{end}/{total_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_len),
            "Content-Disposition": f'inline; filename="{output_id}"',
        }
        return StreamingResponse(
            OutputService.open_byte_range_stream(file_path, start, end),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            media_type=media_type,
            headers=headers,
        )

    # Full content delivery
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(total_size),
        "Content-Disposition": f'inline; filename="{output_id}"',
    }
    return StreamingResponse(
        OutputService.open_byte_range_stream(file_path, 0, total_size - 1),
        status_code=status.HTTP_200_OK,
        media_type=media_type,
        headers=headers,
    )
