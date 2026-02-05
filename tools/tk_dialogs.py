"""Reusable Tk dialog helpers for file/folder selection."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional, Tuple


def _ensure_tkinter():
    try:
        import tkinter as tk  # type: ignore
        from tkinter import filedialog  # type: ignore
    except Exception as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "tkinter is not available. Install it or run with explicit input paths."
        ) from exc

    return tk, filedialog


def _storage_file(base_dir: Path, storage_name: str) -> Path:
    src_dir = base_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    return src_dir / f"{storage_name}.txt"


def _load_last_dir(base_dir: Path, storage_name: str) -> Optional[str]:
    try:
        last_file = _storage_file(base_dir, storage_name)
        if last_file.exists():
            last_dir = last_file.read_text(encoding="utf-8").strip()
            if last_dir and Path(last_dir).exists():
                return last_dir
    except Exception:
        return None
    return None


def _save_last_dir(base_dir: Path, storage_name: str, path: str) -> None:
    try:
        last_file = _storage_file(base_dir, storage_name)
        last_file.write_text(str(Path(path).parent), encoding="utf-8")
    except Exception:
        pass


def select_file_dialog(
    *,
    title: str,
    filetypes: Optional[Iterable[Tuple[str, str]]] = None,
    storage_name: str = "last_opened",
    base_dir: Optional[Path] = None,
    initialdir: Optional[str] = None,
) -> Optional[str]:
    """Open a file dialog and return the selected file path."""
    tk, filedialog = _ensure_tkinter()

    root = tk.Tk()
    root.withdraw()

    try:
        if base_dir is None:
            base_dir = Path.cwd()

        last_dir = initialdir or _load_last_dir(base_dir, storage_name)
        dialog_kwargs = {
            "title": title,
            "filetypes": list(filetypes) if filetypes else [("All files", "*.*")],
        }
        if last_dir:
            dialog_kwargs["initialdir"] = last_dir

        file_path = filedialog.askopenfilename(**dialog_kwargs)
        if file_path:
            _save_last_dir(base_dir, storage_name, file_path)
            return file_path
        return None
    finally:
        try:
            root.destroy()
        except Exception:
            pass


def select_folder_dialog(
    *,
    title: str,
    storage_name: str = "last_opened",
    base_dir: Optional[Path] = None,
    initialdir: Optional[str] = None,
) -> Optional[str]:
    """Open a folder dialog and return the selected directory path."""
    tk, filedialog = _ensure_tkinter()

    root = tk.Tk()
    root.withdraw()

    try:
        if base_dir is None:
            base_dir = Path.cwd()

        last_dir = initialdir or _load_last_dir(base_dir, storage_name)
        dialog_kwargs = {"title": title}
        if last_dir:
            dialog_kwargs["initialdir"] = last_dir

        folder_path = filedialog.askdirectory(**dialog_kwargs)
        if folder_path:
            _save_last_dir(base_dir, storage_name, folder_path)
            return folder_path
        return None
    finally:
        try:
            root.destroy()
        except Exception:
            pass
