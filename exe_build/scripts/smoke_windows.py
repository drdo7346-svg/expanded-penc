"""Launch the actual EXE without a console; exercise native menus/dialogs."""
from pathlib import Path
import ctypes
from ctypes import wintypes as W
import json
import os
import shutil
import subprocess
import time

import psutil
from PIL import ImageGrab


root = Path(__file__).resolve().parents[1]
folder = root / "실행 파일 (한글)"
cwd = root / "시작 경로 (한글)"
folder.mkdir(exist_ok=True)
cwd.mkdir(exist_ok=True)
exe = folder / "PenC_Expansion_Editor.exe"
shutil.copy2(root / "dist" / exe.name, exe)
env = dict(os.environ)
env.pop("PYTHONHOME", None)
env.pop("PYTHONPATH", None)
env.pop("TCL_LIBRARY", None)
env.pop("TK_LIBRARY", None)
# The bundled runtime must work even when installed Python is absent from PATH.
env["PATH"] = str(Path(os.environ["SYSTEMROOT"]) / "System32")
cli = []
for arg, expected in (("--validate-release", 0), ("--layout", 0), ("--invalid-option", 2)):
    result = subprocess.run([str(exe), arg], cwd=cwd, env=env, timeout=90)
    assert result.returncode == expected, (arg, result.returncode)
    cli.append({"argument": arg, "exit_code": result.returncode})

u = ctypes.WinDLL("user32", use_last_error=True)
callback = ctypes.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
u.EnumWindows.argtypes = [callback, W.LPARAM]
u.EnumChildWindows.argtypes = [W.HWND, callback, W.LPARAM]
u.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
u.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
u.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
u.IsWindowVisible.argtypes = [W.HWND]
u.GetMenu.argtypes = [W.HWND]; u.GetMenu.restype = W.HMENU
u.GetSubMenu.argtypes = [W.HMENU, ctypes.c_int]; u.GetSubMenu.restype = W.HMENU
u.GetMenuItemCount.argtypes = [W.HMENU]
u.GetMenuStringW.argtypes = [W.HMENU, W.UINT, W.LPWSTR, ctypes.c_int, W.UINT]
u.GetMenuItemID.argtypes = [W.HMENU, ctypes.c_int]; u.GetMenuItemID.restype = W.UINT
u.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
u.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]


def caption(hwnd, class_name=False):
    text = ctypes.create_unicode_buffer(1024)
    (u.GetClassNameW if class_name else u.GetWindowTextW)(hwnd, text, len(text))
    return text.value


def wait_for(fn, timeout=35):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        if proc.poll() is not None:
            raise AssertionError(f"EXE exited unexpectedly: {proc.returncode}")
        time.sleep(.15)
    raise AssertionError("Window condition timed out")


proc = subprocess.Popen([str(exe)], cwd=cwd, env=env)


def windows():
    p = psutil.Process(proc.pid)
    pids = {p.pid, *(child.pid for child in p.children(recursive=True))}
    result = []
    @callback
    def collect(hwnd, _):
        pid = W.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value in pids and u.IsWindowVisible(hwnd):
            result.append((hwnd, caption(hwnd), caption(hwnd, True)))
        return True
    u.EnumWindows(collect, 0)
    return result


def menu_rows(menu):
    rows = []
    for i in range(u.GetMenuItemCount(menu)):
        value = ctypes.create_unicode_buffer(256)
        u.GetMenuStringW(menu, i, value, len(value), 0x400)
        rows.append((i, value.value.replace("&", ""), u.GetMenuItemID(menu, i)))
    return rows


try:
    hwnd = wait_for(lambda: next((h for h, title, cls in windows()
                                 if cls == "TkTopLevel" and u.GetMenu(h)), None))
    time.sleep(1)
    assert not [x for x in windows() if x[2] == "#32770"], windows()
    menu = u.GetMenu(hwnd)
    rows = menu_rows(menu)
    titles = [r[1] for r in rows]
    credit = next(row for row in rows if row[1] in ("크레딧", "Credits"))
    egg = next(row for row in rows if row[1] in ("알", "Eggs"))
    assert credit[0] == egg[0] + 1, titles
    u.PostMessageW(hwnd, 0x111, credit[2], 0)
    dialog = wait_for(lambda: next((h for h, title, cls in windows()
                                   if cls == "#32770" and title in ("크레딧", "Credits")), None))
    texts = []
    @callback
    def collect_text(child, _):
        texts.append(caption(child))
        return True
    u.EnumChildWindows(dialog, collect_text, 0)
    assert "By DrDo" in texts, texts
    u.PostMessageW(dialog, 0x111, 1, 0)
    wait_for(lambda: not any(x[0] == dialog for x in windows()))
    file_index = next(row[0] for row in rows if row[1] in ("파일", "File"))
    filemenu = u.GetSubMenu(menu, file_index)
    file_rows = menu_rows(filemenu)
    open_rom = next(row for row in file_rows if row[1].split("\t")[0]
                    in ("ROM 열기...", "Open ROM..."))
    u.PostMessageW(hwnd, 0x111, open_rom[2], 0)
    dialog = wait_for(lambda: next((h for h, title, cls in windows()
                                   if cls == "#32770"), None))
    u.PostMessageW(dialog, 0x111, 2, 0)
    wait_for(lambda: not any(x[0] == dialog for x in windows()))
    rect = W.RECT(); u.GetWindowRect(hwnd, ctypes.byref(rect))
    ImageGrab.grab().crop((rect.left, rect.top, rect.right, rect.bottom)).save(root / "windows-gui.png")
    u.PostMessageW(hwnd, 0x10, 0, 0)
    assert proc.wait(timeout=30) == 0
    result = {"cli": cli, "native_gui_launch": True, "credits_dialog": texts,
              "menu_titles": titles, "file_menu_titles": [r[1] for r in file_rows],
              "native_file_dialog_open_cancel": True, "unicode_paths": True,
              "python_and_tcl_removed_from_environment": True, "clean_exit": True}
    (root / "windows-smoke.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("PASS actual EXE: CLI checks, native GUI, Credits, file dialog, Unicode paths and clean close")
finally:
    if proc.poll() is None:
        try:
            children = psutil.Process(proc.pid).children(recursive=True)
        except psutil.Error:
            children = []
        for child in reversed(children):
            try: child.kill()
            except psutil.Error: pass
        proc.kill()

