"""Capture an actual HWND belonging to the specified Java process."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import sys
from PIL import Image,ImageStat

pid=int(sys.argv[1])
title=sys.argv[2]
target=Path(sys.argv[3])
u=C.windll.user32
g=C.windll.gdi32
u.GetWindowThreadProcessId.argtypes=[W.HWND,C.POINTER(W.DWORD)]
u.GetWindowTextLengthW.argtypes=[W.HWND]
u.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,C.c_int]
u.GetWindowRect.argtypes=[W.HWND,C.POINTER(W.RECT)]
u.GetWindowDC.argtypes=[W.HWND]
u.ReleaseDC.argtypes=[W.HWND,W.HDC]
u.PrintWindow.argtypes=[W.HWND,W.HDC,W.UINT]
g.CreateCompatibleDC.argtypes=[W.HDC]
g.CreateCompatibleBitmap.argtypes=[W.HDC,C.c_int,C.c_int]
g.SelectObject.argtypes=[W.HDC,W.HANDLE]
g.DeleteObject.argtypes=[W.HANDLE]
g.DeleteDC.argtypes=[W.HDC]
g.GetDIBits.argtypes=[W.HDC,W.HBITMAP,W.UINT,W.UINT,C.c_void_p,C.c_void_p,W.UINT]
handles=[]
CALLBACK=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
@CALLBACK
def visit(hwnd,param):
    process=W.DWORD()
    u.GetWindowThreadProcessId(hwnd,C.byref(process))
    if process.value==pid:
        n=u.GetWindowTextLengthW(hwnd)
        text=C.create_unicode_buffer(n+1)
        u.GetWindowTextW(hwnd,text,n+1)
        if text.value==title:handles.append(hwnd)
    return True
u.EnumWindows(visit,0)
if not handles:raise SystemExit("No matching app-owned HWND")
hwnd=handles[-1]
rect=W.RECT()
u.GetWindowRect(hwnd,C.byref(rect))
width,height=rect.right-rect.left,rect.bottom-rect.top
u.GetWindowDC.restype=W.HDC
g.CreateCompatibleDC.restype=W.HDC
g.CreateCompatibleBitmap.restype=W.HBITMAP
g.SelectObject.restype=W.HANDLE
dc=u.GetWindowDC(hwnd)
memory=g.CreateCompatibleDC(dc)
bitmap=g.CreateCompatibleBitmap(dc,width,height)
old=g.SelectObject(memory,bitmap)
class Header(C.Structure):
    _fields_=[("size",W.DWORD),("width",W.LONG),("height",W.LONG),("planes",W.WORD),
              ("bits",W.WORD),("compression",W.DWORD),("image_size",W.DWORD),
              ("xppm",W.LONG),("yppm",W.LONG),("colors",W.DWORD),("important",W.DWORD)]
header=Header(C.sizeof(Header),width,height,1,24,0,0,0,0,0,0)
stride=((width*3+3)//4)*4
data=C.create_string_buffer(stride*height)
try:
    if not u.PrintWindow(hwnd,memory,2):raise RuntimeError("PrintWindow did not capture")
    g.SelectObject(memory,old)
    if not g.GetDIBits(memory,bitmap,0,height,data,C.byref(header),0):
        raise RuntimeError("GetDIBits failed")
    image=Image.frombytes("RGB",(width,height),data.raw,"raw","BGR",stride,-1)
    if max(ImageStat.Stat(image).stddev)<2:
        raise RuntimeError("Blank window capture")
    target.parent.mkdir(parents=True,exist_ok=True)
    image.save(target)
    print("Captured actual app HWND using PrintWindow:",title,width,height)
finally:
    g.SelectObject(memory,old)
    g.DeleteObject(bitmap)
    g.DeleteDC(memory)
    u.ReleaseDC(hwnd,dc)
