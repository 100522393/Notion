import os
import sys
import ctypes

EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "export",
}

EXCLUDE_FILES = {
    ".env",
}

VALID_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
}

SPECIAL_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".dockerignore",
    "Makefile",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
}

LANGUAGE_MAP = {
    ".py": "python",
    ".md": "md",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
}


def should_include(path: str) -> bool:
    parts = path.split(os.sep)
    filename = os.path.basename(path)

    if any(part in EXCLUDE_DIRS for part in parts):
        return False

    if filename in EXCLUDE_FILES:
        return False

    if filename in SPECIAL_FILES:
        return True

    _, ext = os.path.splitext(filename)
    return ext in VALID_EXTENSIONS


def get_code_fence_language(filename: str) -> str:
    if filename == "Dockerfile":
        return "dockerfile"
    if filename in {"docker-compose.yml", "docker-compose.yaml", ".dockerignore"}:
        return "yaml"
    if filename == "Makefile":
        return "makefile"

    _, ext = os.path.splitext(filename)
    return LANGUAGE_MAP.get(ext, "text")


def generate_tree(root: str) -> str:
    lines = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

        rel_dir = os.path.relpath(dirpath, root)
        level = 0 if rel_dir == "." else rel_dir.count(os.sep) + 1
        indent = "  " * level

        folder_name = os.path.basename(root) if rel_dir == "." else os.path.basename(dirpath)
        lines.append(f"{indent}- {folder_name}/")

        included_files = []
        for filename in sorted(filenames):
            full_path = os.path.join(dirpath, filename)
            if should_include(full_path):
                included_files.append(filename)

        for filename in included_files:
            lines.append(f"{indent}  - {filename}")

    return "\n".join(lines)


def copy_file_to_clipboard(file_path: str) -> None:
    if sys.platform != "win32":
        print("⚠️ Copiar archivos al portapapeles solo está soportado en Windows.")
        return

    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        print(f"⚠️ No existe el archivo: {file_path}")
        return

    # API Win32
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    GMEM_MOVEABLE = 0x0002
    GMEM_ZEROINIT = 0x0040
    GHND = GMEM_MOVEABLE | GMEM_ZEROINIT
    CF_HDROP = 15

    # Configurar tipos correctamente (clave para 64-bit)
    kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = ctypes.c_void_p

    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalLock.restype = ctypes.c_void_p

    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = ctypes.c_int

    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p

    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = ctypes.c_int

    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.c_int

    user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    user32.SetClipboardData.restype = ctypes.c_void_p

    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.c_int

    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", ctypes.c_uint32),
            ("pt_x", ctypes.c_long),
            ("pt_y", ctypes.c_long),
            ("fNC", ctypes.c_int),
            ("fWide", ctypes.c_int),
        ]

    dropfiles = DROPFILES()
    dropfiles.pFiles = ctypes.sizeof(DROPFILES)
    dropfiles.pt_x = 0
    dropfiles.pt_y = 0
    dropfiles.fNC = 0
    dropfiles.fWide = 1

    # Lista doblemente terminada en null, UTF-16LE
    file_data = (file_path + "\0\0").encode("utf-16le")
    total_size = ctypes.sizeof(DROPFILES) + len(file_data)

    h_global = kernel32.GlobalAlloc(GHND, total_size)
    if not h_global:
        raise OSError(f"GlobalAlloc falló. GetLastError={ctypes.get_last_error()}")

    p_global = kernel32.GlobalLock(h_global)
    if not p_global:
        kernel32.GlobalFree(h_global)
        raise OSError(f"GlobalLock falló. GetLastError={ctypes.get_last_error()}")

    try:
        ctypes.memmove(p_global, ctypes.byref(dropfiles), ctypes.sizeof(DROPFILES))
        ctypes.memmove(
            p_global + ctypes.sizeof(DROPFILES),
            file_data,
            len(file_data),
        )
    finally:
        kernel32.GlobalUnlock(h_global)

    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(h_global)
        raise OSError(f"OpenClipboard falló. GetLastError={ctypes.get_last_error()}")

    try:
        if not user32.EmptyClipboard():
            kernel32.GlobalFree(h_global)
            raise OSError(f"EmptyClipboard falló. GetLastError={ctypes.get_last_error()}")

        if not user32.SetClipboardData(CF_HDROP, h_global):
            kernel32.GlobalFree(h_global)
            raise OSError(f"SetClipboardData falló. GetLastError={ctypes.get_last_error()}")

        # Si SetClipboardData funciona, Windows pasa a ser dueño de la memoria
        h_global = None
    finally:
        user32.CloseClipboard()

    print("Archivo copiado al portapapeles")


def generate_md(root: str, output: str = "contexto_proyecto.md") -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(root)
    output = os.path.join(script_dir, output)
    project_name = os.path.basename(root)

    with open(output, "w", encoding="utf-8") as out:
        out.write(f"# Proyecto: {project_name}\n\n")

        out.write("## Estructura\n\n")
        out.write("```text\n")
        out.write(generate_tree(root))
        out.write("\n```\n\n")

        out.write("## Archivos\n")

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]

            for filename in sorted(filenames):
                full_path = os.path.join(dirpath, filename)

                if not should_include(full_path):
                    continue

                rel_path = os.path.relpath(full_path, root)
                language = get_code_fence_language(filename)

                out.write(f"\n### `{rel_path}`\n\n")
                out.write(f"```{language}\n")

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        out.write(f.read())
                except UnicodeDecodeError:
                    out.write("[No se pudo leer el archivo como texto UTF-8]")
                except Exception as e:
                    out.write(f"[Error al leer el archivo: {e}]")

                out.write("\n```\n")

    print(f"Generado: {output}")
    return output


if __name__ == "__main__":
    generated_file = generate_md("..")
    copy_file_to_clipboard(generated_file)