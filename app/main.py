import os
import sys
import stat
import math
import datetime
import subprocess
import uuid
import logging
import fnmatch
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (stdout is the MCP transport channel)
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("manim-mcp")

mcp = FastMCP("manim-mcp")

# Define allowed base directories for security
ALLOWED_BASE_DIRS = [
    "/manim",
    "/app",
    "/media",
    "/usr/local",
    "/tmp"
]


def _check_path_security(filepath: str) -> Optional[str]:
    """Check path security. Returns error message if invalid, None if OK."""
    filepath = os.path.normpath(filepath)

    if ".." in filepath.split(os.sep):
        return "Path traversal attempts are not allowed"

    if not any(filepath == base or filepath.startswith(f"{base}/") for base in ALLOWED_BASE_DIRS):
        return f"Access is only allowed to these base directories: {', '.join(ALLOWED_BASE_DIRS)}"

    return None


def get_file_info(file_path: str, base_dir: str) -> dict:
    """Get detailed information about a file or directory."""
    try:
        stat_info = os.stat(file_path)
        is_dir = os.path.isdir(file_path)
        rel_path = os.path.relpath(file_path, base_dir) if base_dir != file_path else ""

        size = stat_info.st_size if not is_dir else 0

        mtime = datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat()
        ctime = datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat()

        mode = stat_info.st_mode
        perms = ""
        for who in "USR", "GRP", "OTH":
            for what in "R", "W", "X":
                perms += what if mode & getattr(stat, f"S_I{what}{who}") else "-"

        return {
            "name": os.path.basename(file_path),
            "path": file_path,
            "relative_path": rel_path,
            "is_dir": is_dir,
            "size": size,
            "size_human": format_size(size),
            "modified_time": mtime,
            "created_time": ctime,
            "permissions": perms,
        }
    except (FileNotFoundError, PermissionError):
        return {
            "name": os.path.basename(file_path),
            "path": file_path,
            "relative_path": os.path.relpath(file_path, base_dir) if base_dir != file_path else "",
            "is_dir": os.path.isdir(file_path) if os.path.exists(file_path) else None,
            "error": "Permission denied or file not found"
        }


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0B"

    size_names = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.2f}{size_names[i]}"


@mcp.tool()
def list_files(
    directory: str = "/manim",
    recursive: bool = False,
    show_hidden: bool = False,
    max_depth: int = 1,
    pattern: Optional[str] = None,
) -> dict:
    """List files and directories in the Docker container filesystem.

    Args:
        directory: Directory path to list (must be under an allowed base directory)
        recursive: Whether to list files recursively
        show_hidden: Whether to show hidden files (starting with .)
        max_depth: Maximum depth for recursive listing
        pattern: Filter files by pattern (glob syntax)
    """
    directory = os.path.normpath(directory)

    error = _check_path_security(directory)
    if error:
        return {"error": error}

    if not os.path.exists(directory):
        return {"error": f"Directory not found: {directory}"}

    if not os.path.isdir(directory):
        return {"error": f"Path is not a directory: {directory}"}

    results = []

    if recursive:
        for root, dirs, files in os.walk(directory):
            relative_path = os.path.relpath(root, directory)
            depth = len(relative_path.split(os.sep)) if relative_path != "." else 0

            if depth > max_depth:
                continue

            if not show_hidden:
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                files = [f for f in files if not f.startswith('.')]

            if pattern:
                files = [f for f in files if fnmatch.fnmatch(f, pattern)]

            for filename in files:
                file_path = os.path.join(root, filename)
                results.append(get_file_info(file_path, directory))

            for dirname in dirs:
                dir_path = os.path.join(root, dirname)
                results.append(get_file_info(dir_path, directory))
    else:
        try:
            entries = os.listdir(directory)

            if not show_hidden:
                entries = [entry for entry in entries if not entry.startswith('.')]

            if pattern:
                entries = [entry for entry in entries if fnmatch.fnmatch(entry, pattern)]

            for entry in entries:
                entry_path = os.path.join(directory, entry)
                results.append(get_file_info(entry_path, directory))

        except PermissionError:
            return {"error": f"Permission denied: {directory}"}

    results.sort(key=lambda x: (not x.get("is_dir", False), x["name"]))

    return {
        "directory": directory,
        "parent_directory": os.path.dirname(directory) if directory != "/" else None,
        "count": len(results),
        "results": results
    }


@mcp.tool()
def write_file(
    filepath: str,
    content: str,
    overwrite: bool = False,
    create_dirs: bool = True,
) -> dict:
    """Write content to a file in the Docker container filesystem.

    Args:
        filepath: Path where the file should be written, including filename
        content: Content to write to the file
        overwrite: Whether to overwrite existing files
        create_dirs: Whether to create parent directories if they don't exist
    """
    filepath = os.path.normpath(filepath)

    error = _check_path_security(filepath)
    if error:
        return {"error": error}

    directory = os.path.dirname(filepath)

    if not os.path.exists(directory):
        if create_dirs:
            try:
                os.makedirs(directory, exist_ok=True)
            except PermissionError:
                return {"error": f"Permission denied: Cannot create directory {directory}"}
            except Exception as e:
                return {"error": f"Failed to create directory {directory}: {str(e)}"}
        else:
            return {"error": f"Directory not found: {directory}"}

    if os.path.exists(filepath) and not overwrite:
        return {"error": f"File already exists: {filepath}. Use overwrite=true to replace it."}

    try:
        with open(filepath, 'w') as file:
            file.write(content)

        file_info = get_file_info(filepath, os.path.dirname(filepath))

        return {
            "status": "success",
            "message": "File written successfully",
            "file": file_info,
        }
    except PermissionError:
        return {"error": f"Permission denied: Cannot write to {filepath}"}
    except Exception as e:
        return {"error": f"Failed to write file: {str(e)}"}


@mcp.tool()
def read_file(filepath: str) -> dict:
    """Read a file's contents from the Docker container filesystem.

    Args:
        filepath: Path to the file to read
    """
    filepath = os.path.normpath(filepath)

    error = _check_path_security(filepath)
    if error:
        return {"error": error}

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    if not os.path.isfile(filepath):
        return {"error": f"Path is not a file: {filepath}"}

    try:
        with open(filepath, 'r') as f:
            content = f.read()

        file_info = get_file_info(filepath, os.path.dirname(filepath))

        return {
            "status": "success",
            "file": file_info,
            "content": content,
        }
    except UnicodeDecodeError:
        return {"error": f"File is not a text file: {filepath}. Binary files cannot be read."}
    except PermissionError:
        return {"error": f"Permission denied: Cannot read {filepath}"}
    except Exception as e:
        return {"error": f"Failed to read file: {str(e)}"}


@mcp.tool()
def render_latex(
    expressions: list[str],
    math_mode: bool = True,
    text_only: bool = False,
    color: str = "WHITE",
    background_color: Optional[str] = None,
    font_size: int = 48,
    quality: str = "medium_quality",
    format: str = "png",
    transparent: bool = False,
    arrangement: str = "vertical",
    buff: float = 0.5,
    template: Optional[str] = None,
    additional_preamble: Optional[str] = None,
) -> dict:
    """Render LaTeX/MathTeX expressions directly as images without writing a full Manim scene.

    This is a convenience tool that generates and renders a Manim scene from LaTeX expressions.
    Use this for quickly rendering mathematical formulas, equations, or formatted text.

    There are three rendering modes controlled by math_mode and text_only:

    1. MathTex mode (math_mode=True, text_only=False) — default. Renders LaTeX math expressions
       using MathTex. Requires dvisvgm to be installed in the container.
       Example expressions: [r"E = mc^2", r"\\int_0^1 x^2 dx"]

    2. Tex mode (math_mode=False, text_only=False) — renders LaTeX with mixed text and inline
       math (use $...$ for math). Requires dvisvgm to be installed in the container.
       Example expressions: [r"The area is $A = \\pi r^2$"]

    3. Text mode (text_only=True) — uses Manim's Text() renderer (Pango/Cairo). Does NOT require
       LaTeX or dvisvgm. No math typesetting, but always works. Use this as a fallback when
       LaTeX rendering fails due to missing dvisvgm.
       Example expressions: ["E = mc²", "Hello World"]

    Args:
        expressions: List of expression strings to render
        math_mode: If True, use MathTex (math mode). If False, use Tex (text mode with inline math via $...$). Ignored when text_only=True.
        text_only: If True, use Manim's Text() instead of MathTex/Tex. No LaTeX required — always works. No math typesetting.
        color: Text color as a Manim color name (e.g., 'WHITE', 'BLUE', 'YELLOW') or hex (e.g., '#ff0000')
        background_color: Background color. None uses Manim default (BLACK). Use hex or color name.
        font_size: Font size for the text (default 48)
        quality: Quality setting - low_quality (480p/15fps), medium_quality (720p/30fps), high_quality (1080p/60fps), production_quality (1440p/60fps)
        format: Output format - 'png' (default, saves last frame) or 'mp4'/'gif' (animated write-on effect)
        transparent: Render with transparent background (useful for overlays)
        arrangement: How to arrange multiple expressions - 'vertical' (top to bottom), 'horizontal' (left to right), or 'grid'
        buff: Spacing between expressions when multiple are provided
        template: LaTeX template name if needed (e.g., 'TexFontTemplates' member). Ignored when text_only=True.
        additional_preamble: Extra LaTeX preamble commands (e.g., r"\\usepackage{amssymb}"). Ignored when text_only=True.
    """
    if not expressions:
        return {"error": "At least one expression is required"}

    job_id = str(uuid.uuid4())
    output_dir = f"/manim/output/{job_id}"
    scene_file = f"/tmp/latex_{job_id}.py"
    os.makedirs(output_dir, exist_ok=True)

    # Determine which Manim class to use
    if text_only:
        tex_class = "Text"
    elif math_mode:
        tex_class = "MathTex"
    else:
        tex_class = "Tex"

    # Escape expressions for embedding in Python string literals
    escaped = []
    for expr in expressions:
        if text_only:
            # For Text(), just escape quotes — no LaTeX backslash handling
            escaped.append(expr.replace('\\', '\\\\').replace('"', '\\"'))
        else:
            escaped.append(expr.replace('\\', '\\\\').replace('"', '\\"'))

    lines = [
        "from manim import *",
        "",
    ]

    # Add custom template/preamble if provided (LaTeX modes only)
    if additional_preamble and not text_only:
        lines.append(f'preamble = TexTemplate()')
        lines.append(f'preamble.add_to_preamble(r"""{additional_preamble}""")')
        lines.append("")

    lines.append("class LatexScene(Scene):")
    lines.append("    def construct(self):")

    # Create each expression
    tex_objects = []
    for i, expr in enumerate(escaped):
        var = f"tex_{i}"
        tex_objects.append(var)

        if text_only:
            lines.append(f'        {var} = Text("{expr}", font_size={font_size})')
        else:
            template_arg = ", tex_template=preamble" if additional_preamble else ""
            lines.append(f'        {var} = {tex_class}(r"{expr}", font_size={font_size}{template_arg})')

        # Handle color - check if it's a hex color or a named color
        if color.startswith('#'):
            lines.append(f'        {var}.set_color("{color}")')
        else:
            lines.append(f'        {var}.set_color({color})')

    # Arrange expressions
    if len(tex_objects) > 1:
        group_items = ", ".join(tex_objects)
        lines.append(f"        group = VGroup({group_items})")
        if arrangement == "horizontal":
            lines.append(f"        group.arrange(RIGHT, buff={buff})")
        elif arrangement == "grid":
            # Auto grid: roughly square layout
            cols = math.ceil(math.sqrt(len(tex_objects)))
            lines.append(f"        group.arrange_in_grid(cols={cols}, buff={buff})")
        else:  # vertical (default)
            lines.append(f"        group.arrange(DOWN, buff={buff})")
        lines.append("        group.move_to(ORIGIN)")
        # Scale to fit if needed
        lines.append("        if group.width > config.frame_width - 1:")
        lines.append("            group.scale_to_fit_width(config.frame_width - 1)")
        lines.append("        if group.height > config.frame_height - 1:")
        lines.append("            group.scale_to_fit_height(config.frame_height - 1)")
    else:
        # Single expression - scale to fit
        lines.append(f"        if {tex_objects[0]}.width > config.frame_width - 1:")
        lines.append(f"            {tex_objects[0]}.scale_to_fit_width(config.frame_width - 1)")

    # Determine if we animate or just show the last frame
    is_static = (format == "png")

    if is_static:
        for var in tex_objects:
            lines.append(f"        self.add({var})")
    else:
        if len(tex_objects) > 1:
            lines.append("        self.play(Write(group))")
        else:
            lines.append(f"        self.play(Write({tex_objects[0]}))")
        lines.append("        self.wait(1)")

    scene_code = "\n".join(lines) + "\n"

    try:
        with open(scene_file, 'w') as f:
            f.write(scene_code)
    except Exception as e:
        return {"error": f"Failed to write scene file: {str(e)}"}

    # Build manim command
    cmd = ["python3", "-m", "manim"]

    quality_map = {
        "low_quality": "-ql",
        "medium_quality": "-qm",
        "high_quality": "-qh",
        "production_quality": "-qk",
    }
    if quality in quality_map:
        cmd.append(quality_map[quality])

    if transparent:
        cmd.append("-t")

    if is_static:
        cmd.append("--save_last_frame")

    if format and format != "png":
        cmd.extend(["--format", format])

    if background_color:
        cmd.extend(["-c", background_color])

    cmd.extend(["--output_file", output_dir])
    cmd.append(scene_file)
    cmd.append("LatexScene")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        files = []
        file_info = []

        if os.path.exists(output_dir):
            dir_files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
            for file in dir_files:
                file_path = os.path.join(output_dir, file)
                info = get_file_info(file_path, output_dir)
                file_info.append(info)
                files.append(file)

        parent_output_dir = "/manim/output"
        if os.path.exists(parent_output_dir):
            parent_files = [f for f in os.listdir(parent_output_dir)
                          if os.path.isfile(os.path.join(parent_output_dir, f)) and job_id in f]
            for file in parent_files:
                file_path = os.path.join(parent_output_dir, file)
                info = get_file_info(file_path, parent_output_dir)
                file_info.append(info)
                files.append(file)

        return {
            "job_id": job_id,
            "status": "success",
            "mode": "text" if text_only else ("mathtex" if math_mode else "tex"),
            "command": " ".join(cmd),
            "output": result.stdout,
            "scene_code": scene_code,
            "files": file_info,
            "output_directory": output_dir,
        }

    except subprocess.CalledProcessError as e:
        return {
            "job_id": job_id,
            "status": "error",
            "mode": "text" if text_only else ("mathtex" if math_mode else "tex"),
            "command": " ".join(cmd),
            "scene_code": scene_code,
            "error": e.stderr,
            "returncode": e.returncode,
        }
    finally:
        # Clean up temp scene file
        try:
            os.remove(scene_file)
        except OSError:
            pass


@mcp.tool()
def run_manim(
    filepath: str,
    scene_name: str,
    quality: str = "medium_quality",
    preview: bool = False,
    format: Optional[str] = None,
    transparent: bool = False,
    save_last_frame: bool = False,
    from_animation_number: Optional[int] = None,
    upto_animation_number: Optional[int] = None,
    resolution: Optional[str] = None,
    frame_rate: Optional[int] = None,
    color: Optional[str] = None,
    additional_args: Optional[list[str]] = None,
) -> dict:
    """Run Manim on a Python file to generate a mathematical animation.

    Manim is a mathematical animation engine for creating explanatory math videos.
    This tool runs Manim with the specified options and returns information about the generated output.
    Output files are available via the mounted volume at /manim/output.

    Args:
        filepath: Path to the Python file with Manim scenes (must be under an allowed base directory)
        scene_name: Name of the scene class to render
        quality: Quality setting - low_quality (480p/15fps), medium_quality (720p/30fps), high_quality (1080p/60fps), production_quality (1440p/60fps)
        preview: Whether to add the preview flag (-p)
        format: Output format (e.g., 'png', 'gif', 'mp4', 'webm')
        transparent: Render background as transparent (-t flag)
        save_last_frame: Only render the last frame of the scene
        from_animation_number: Start rendering from a specific animation number
        upto_animation_number: End rendering at a specific animation number
        resolution: Resolution as WIDTHxHEIGHT (e.g., '1920x1080')
        frame_rate: Frame rate in frames per second
        color: Background color (e.g., '#ffffff', 'WHITE')
        additional_args: Additional command-line arguments to pass to Manim
    """
    filepath = os.path.normpath(filepath)

    error = _check_path_security(filepath)
    if error:
        return {"error": error}

    if not os.path.exists(filepath):
        return {"error": f"File not found: {filepath}"}

    if not os.path.isfile(filepath):
        return {"error": f"Path is not a file: {filepath}"}

    job_id = str(uuid.uuid4())
    output_dir = f"/manim/output/{job_id}"
    os.makedirs(output_dir, exist_ok=True)

    cmd = ["python3", "-m", "manim"]

    quality_map = {
        "low_quality": "-ql",
        "medium_quality": "-qm",
        "high_quality": "-qh",
        "production_quality": "-qk",
    }
    if quality in quality_map:
        cmd.append(quality_map[quality])

    if preview:
        cmd.append("-p")

    if transparent:
        cmd.append("-t")

    if save_last_frame:
        cmd.append("--save_last_frame")

    if format:
        cmd.extend(["--format", format])

    if resolution:
        cmd.extend(["-r", resolution])

    if frame_rate:
        cmd.extend(["-f", str(frame_rate)])

    if color:
        cmd.extend(["-c", color])

    if from_animation_number is not None or upto_animation_number is not None:
        anim_range = []
        if from_animation_number is not None:
            anim_range.append(str(from_animation_number))
        else:
            anim_range.append("")

        if upto_animation_number is not None:
            anim_range.append(str(upto_animation_number))

        cmd.extend(["-n", ",".join(anim_range)])

    cmd.extend(["--output_file", output_dir])
    cmd.append(filepath)
    cmd.append(scene_name)

    if additional_args:
        cmd.extend(additional_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )

        files = []
        file_info = []

        if os.path.exists(output_dir):
            dir_files = [f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))]
            for file in dir_files:
                file_path = os.path.join(output_dir, file)
                info = get_file_info(file_path, output_dir)
                file_info.append(info)
                files.append(file)

        parent_output_dir = "/manim/output"
        if os.path.exists(parent_output_dir):
            parent_files = [f for f in os.listdir(parent_output_dir)
                          if os.path.isfile(os.path.join(parent_output_dir, f)) and job_id in f]
            for file in parent_files:
                file_path = os.path.join(parent_output_dir, file)
                info = get_file_info(file_path, parent_output_dir)
                file_info.append(info)
                files.append(file)

        return {
            "job_id": job_id,
            "status": "success",
            "command": " ".join(cmd),
            "output": result.stdout,
            "files": file_info,
            "output_directory": output_dir,
        }

    except subprocess.CalledProcessError as e:
        return {
            "job_id": job_id,
            "status": "error",
            "command": " ".join(cmd),
            "error": e.stderr,
            "returncode": e.returncode,
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
