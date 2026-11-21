"""Footage interpretation, proxies and relinking a missing file by its name."""

from typing import Annotated, Literal

from cavi_mcp_core.server import WRITES, need, reject_foreign
from pydantic import Field

from .. import host, models
from ..app import Project, given, mcp, scene

# Fields each action reads. item is accepted by every action and checked on its own.
FOOTAGE_USES = {
    "info": set(),
    "interpret": {"alpha", "invert_alpha", "conform_fps", "pixel_aspect"},
    "proxy": {"file", "clear", "use_proxy"},
    "relink": {"folder"},
}


@mcp.tool(annotations=WRITES)
async def ae_footage(
        project: Project,
        action: Annotated[Literal["info", "interpret", "proxy", "relink"],
                          Field(description="info reports interpretation, interpret sets it, proxy sets or "
                                            "clears a proxy, relink replaces missing footage by file name.")],
        item: Annotated[int | Annotated[str, Field(min_length=1)] | None,
                        Field(description="Footage name or project item id. Required for info, "
                                          "interpret and proxy. Omit on relink to scan every missing "
                                          "item.")] = None,
        alpha: Annotated[Literal["ignore", "straight", "premultiplied"] | None,
                         Field(description="Alpha mode interpret sets.")] = None,
        invert_alpha: Annotated[bool | None,
                                Field(description="Whether interpret inverts the alpha.")] = None,
        conform_fps: Annotated[Annotated[float, Field(ge=0, le=99)] | None,
                               Field(description="Frame rate interpret conforms to; 0 restores the native "
                                                 "rate. A still is refused.")] = None,
        pixel_aspect: Annotated[Annotated[float, Field(gt=0)] | None,
                                Field(description="Pixel aspect ratio interpret sets.")] = None,
        file: Annotated[str | None, Field(description="Absolute path of the proxy file proxy sets.")] = None,
        clear: Annotated[bool, Field(description="Remove the proxy. Refused together with file.")] = False,
        use_proxy: Annotated[bool | None, Field(description="Use the proxy instead of the footage, without "
                                                            "replacing the proxy file.")] = None,
        folder: Annotated[str | None, Field(description="Absolute directory relink walks, matching missing "
                                                        "footage by file name.")] = None
) -> models.FootageEdited:
    """Report or set footage interpretation and proxy, or relink missing footage by file name. A still refuses
    conform_fps, and a conform rate of 0 restores the clip's native frame rate."""
    reject_foreign(action, {
        "alpha": alpha, "invert_alpha": invert_alpha, "conform_fps": conform_fps,
        "pixel_aspect": pixel_aspect, "file": file or None, "clear": clear or None,
        "use_proxy": use_proxy, "folder": folder or None,
    }, FOOTAGE_USES[action])
    if action in ("info", "interpret", "proxy"):
        need(item, "item", action)
    if action == "interpret":
        given(alpha=alpha, invert_alpha=invert_alpha, conform_fps=conform_fps, pixel_aspect=pixel_aspect)
    if action == "proxy":
        if file is None and not clear and use_proxy is None:
            raise ValueError("Give at least one of: file, clear, use_proxy")
        if clear and file is not None:
            raise ValueError("Give file or clear, not both")
        if file is not None:
            file = str(host.absolute(file))
    if action == "relink":
        need(folder, "folder", action)
        folder_path = host.absolute(folder)
        if not folder_path.is_dir():
            raise FileNotFoundError(f"No folder at {folder_path}")
        folder = str(folder_path)
    return await scene("ae_footage", project, {
        "action": action, "item": item, "alpha": alpha, "invert_alpha": invert_alpha,
        "conform_fps": conform_fps, "pixel_aspect": pixel_aspect, "file": file, "clear": clear,
        "use_proxy": use_proxy, "folder": folder})
