"""Desktop cell annotation with optional, individually reviewable suggestions."""

import argparse
import copy
from datetime import datetime, timezone
import math
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from src.eval.common import ROOT, sha256
from src.eval.cell_proposals import otsu_threshold, propose_boxes
from src.eval.prepare_ground_truth import (image_array, overlay, read_json,
                                          validate_cell_truth, write_json)


def object_from_box(box, identifier):
    x0, y0, x1, y1 = box
    return {"id": identifier, "x": (x0+x1)/2, "y": (y0+y1)/2,
            "radius": math.sqrt((x1-x0)*(y1-y0))/2, "bbox_xyxy": list(box)}


class CellAnnotator:
    def __init__(self, window, root):
        self.window, self.root = window, root
        self.path = root / "data/gt/blob/blob_05.json"
        self.raw_path = root / "data/raw/blob_05.png"
        self.raw = image_array(self.raw_path)
        self.digest = sha256(self.raw_path)
        self.truth = read_json(self.path)
        self.saved_file_digest = sha256(self.path)
        validate_cell_truth(self.truth, "blob_05", self.raw, self.digest)
        self.base_image = Image.fromarray(self.raw)
        self.history, self.drag_start, self.drag_item = [], None, None
        self.dirty = False
        self.edit_index = None
        self.threshold = tk.StringVar(value=str(max(1, round(.85*otsu_threshold(self.raw)))))
        self.zoom = tk.StringVar(value="2")
        self.mode = tk.StringVar(value="object")
        self.reviewer = tk.StringVar(value=self.truth.get("reviewer", ""))
        self.status = tk.StringVar()
        window.title("Duc 05/11 - Gan nhan thu cong blob_05")
        window.geometry("1100x850")
        toolbar = ttk.Frame(window, padding=6)
        toolbar.pack(fill="x")
        for label, command in (("Luu nhap", self.save_draft), ("Da ra soat toan anh", self.complete),
                                ("Hoan tac", self.undo), ("Xoa muc chon", self.delete_selected)):
            ttk.Button(toolbar, text=label, command=command).pack(side="left", padx=3)
        ttk.Label(toolbar, text="Nguoi gan nhan:").pack(side="left", padx=5)
        ttk.Entry(toolbar, textvariable=self.reviewer, width=18).pack(side="left")
        options = ttk.Frame(window, padding=5)
        options.pack(fill="x")
        ttk.Radiobutton(options, text="Khoanh doi tuong (xanh)", variable=self.mode, value="object").pack(side="left")
        ttk.Radiobutton(options, text="Vung bo qua (cam)", variable=self.mode, value="ignore").pack(side="left")
        ttk.Label(options, text="Phong to:").pack(side="left", padx=10)
        selector = ttk.Combobox(options, textvariable=self.zoom, values=("1", "2", "3"), state="readonly", width=3)
        selector.pack(side="left")
        selector.bind("<<ComboboxSelected>>", lambda event: self.redraw())
        assistance = ttk.Frame(window, padding=5)
        assistance.pack(fill="x")
        ttk.Label(assistance, text="Nguong goi y:").pack(side="left")
        ttk.Entry(assistance, textvariable=self.threshold, width=4).pack(side="left", padx=3)
        for label, command in (("Tao goi y", self.add_suggestions), ("Duyet muc chon [Enter]", self.accept_selected),
                                ("Goi y tiep [N]", self.next_suggestion), ("Ve lai muc chon", self.edit_selected),
                                ("Duyet vung dang xem", self.accept_visible)):
            ttk.Button(assistance, text=label, command=command).pack(side="left", padx=2)
        ttk.Label(window, text="Tim/hong = goi y CHUA DUYET. Xem ky tung vung, xoa/sua khung sai, ve them cho bi sot; sau do duyet. Nhan chuot vao doi tuong de chon. Vung cam de bo qua cum khong ro.", wraplength=1050).pack(fill="x", padx=8)
        body = ttk.Frame(window)
        body.pack(fill="both", expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(body, background="#202020", cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(xscrollcommand=horizontal.set, yscrollcommand=vertical.set)
        self.items = tk.Listbox(body, width=30, exportselection=False)
        self.items.grid(row=0, column=2, sticky="nsew")
        self.items.bind("<<ListboxSelect>>", lambda event: self.redraw_image())
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.move_drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<Return>", lambda event: self.accept_selected())
        self.canvas.bind("<Key-n>", lambda event: self.next_suggestion())
        self.canvas.bind("<Delete>", lambda event: self.delete_selected())
        self.items.bind("<Return>", lambda event: self.accept_selected())
        self.items.bind("<Key-n>", lambda event: self.next_suggestion())
        self.items.bind("<Delete>", lambda event: self.delete_selected())
        ttk.Label(window, textvariable=self.status, padding=6).pack(fill="x")
        window.protocol("WM_DELETE_WINDOW", self.close)
        self.redraw()

    @property
    def scale(self):
        return int(self.zoom.get())

    def coordinates(self, event):
        x = max(0., min(self.raw.shape[1]-1., self.canvas.canvasx(event.x)/self.scale))
        y = max(0., min(self.raw.shape[0]-1., self.canvas.canvasy(event.y)/self.scale))
        return x, y

    def remember(self):
        self.history.append(copy.deepcopy(self.truth))
        self.truth["reviewed"] = False
        self.truth["status"] = "DRAFT"
        self.dirty = True

    def start_drag(self, event):
        self.canvas.focus_set()
        self.drag_start = self.coordinates(event)

    def move_drag(self, event):
        if self.drag_start is None:
            return
        x, y = self.coordinates(event)
        if self.drag_item is not None:
            self.canvas.delete(self.drag_item)
        coords = [self.scale*v for v in (*self.drag_start, x, y)]
        self.drag_item = self.canvas.create_rectangle(*coords, outline="yellow", width=2)

    def end_drag(self, event):
        if self.drag_start is None:
            return
        x, y = self.coordinates(event)
        sx, sy = self.drag_start
        self.drag_start = None
        if self.drag_item is not None:
            self.canvas.delete(self.drag_item)
            self.drag_item = None
        box = [round(min(sx,x), 2), round(min(sy,y), 2), round(max(sx,x), 2), round(max(sy,y), 2)]
        if box[2]-box[0] < 2 or box[3]-box[1] < 2:
            self.edit_index = None
            self.select_at(x,y)
            return
        self.remember()
        if self.edit_index is not None:
            index = self.edit_index
            if index < len(self.truth["objects"]):
                item = self.truth["objects"][index]
                self.truth["objects"][index] = dict(item, **object_from_box(box,index+1), human_adjusted=True)
                if item.get("annotation_method") == "threshold_component_suggestion":
                    self.truth["objects"][index]["proposal_reviewed"] = True
            else:
                self.truth["ignore_regions"][index-len(self.truth["objects"])]=box
            self.edit_index = None
        elif self.mode.get() == "ignore":
            self.truth["objects"] = [item for item in self.truth["objects"]
                                     if not (self.is_pending(item) and box[0] <= item["x"] <= box[2] and box[1] <= item["y"] <= box[3])]
            self.truth["ignore_regions"].append(box)
        else:
            self.truth["objects"].append(object_from_box(box, len(self.truth["objects"])+1))
        self.redraw()

    def redraw(self):
        selected = self.items.curselection()
        self.items.delete(0, "end")
        for index, item in enumerate(self.truth["objects"], 1):
            item["id"] = index
            pending = self.is_pending(item)
            self.items.insert("end", f"{'? ' if pending else ''}{index}: x={item['x']:.1f}, y={item['y']:.1f}, r={item['radius']:.1f}")
            if pending:
                self.items.itemconfig(index-1, fg="#a000a0")
        for index, box in enumerate(self.truth["ignore_regions"], 1):
            self.items.insert("end", f"Bo qua {index}: ({box[0]:.0f},{box[1]:.0f})")
        if selected and selected[0] < self.items.size():
            self.items.selection_set(selected[0])
        self.redraw_image()

    def redraw_image(self):
        picture = overlay(self.raw, objects=self.truth["objects"], ignores=self.truth["ignore_regions"])
        selected = self.items.curselection()
        if selected:
            index = selected[0]
            if index < len(self.truth["objects"]):
                box = self.truth["objects"][index]["bbox_xyxy"]
            else:
                box = self.truth["ignore_regions"][index-len(self.truth["objects"])]
            ImageDraw.Draw(picture).rectangle(tuple(box), outline="red", width=2)
        self.photo = ImageTk.PhotoImage(picture.resize((self.raw.shape[1]*self.scale, self.raw.shape[0]*self.scale), Image.Resampling.NEAREST))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.photo)
        self.canvas.configure(scrollregion=(0, 0, self.photo.width(), self.photo.height()))
        pending = sum(self.is_pending(item) for item in self.truth["objects"])
        attention = ""
        if selected and selected[0] < len(self.truth["objects"]) and self.truth["objects"][selected[0]].get("suggestion_flags"):
            attention = " | Co the la cum dinh/doi tuong dai: xem ky, tach hoac bo qua"
        self.status.set(f"{len(self.truth['objects'])} doi tuong, {pending} goi y CHUA DUYET; {len(self.truth['ignore_regions'])} vung bo qua | {self.truth['status']} | {'Chua luu' if self.dirty else 'Da luu'}{attention}")

    @staticmethod
    def is_pending(item):
        return item.get("annotation_method") == "threshold_component_suggestion" and not item.get("proposal_reviewed", False)

    def select_index(self, index, reveal=False):
        self.items.selection_clear(0,"end")
        self.items.selection_set(index)
        self.items.see(index)
        self.redraw_image()
        if reveal and index < len(self.truth["objects"]):
            item = self.truth["objects"][index]
            self.canvas.xview_moveto(max(0,(item["x"]*self.scale-self.canvas.winfo_width()/2)/(self.raw.shape[1]*self.scale)))
            self.canvas.yview_moveto(max(0,(item["y"]*self.scale-self.canvas.winfo_height()/2)/(self.raw.shape[0]*self.scale)))

    def select_at(self, x, y):
        candidates = [(math.hypot(item["x"]-x,item["y"]-y),index) for index,item in enumerate(self.truth["objects"])
                      if math.hypot(item["x"]-x,item["y"]-y) <= max(item["radius"]+3,7)]
        if candidates:
            self.select_index(min(candidates)[1])
        else:
            for index,box in enumerate(self.truth["ignore_regions"]):
                if box[0]<=x<=box[2] and box[1]<=y<=box[3]:
                    self.select_index(len(self.truth["objects"])+index)
                    break

    def add_suggestions(self):
        try:
            threshold = int(self.threshold.get())
            proposals = propose_boxes(self.raw,self.truth["objects"],self.truth["ignore_regions"],threshold=threshold)
        except ValueError as error:
            messagebox.showerror("Nguong chua hop le",str(error),parent=self.window)
            return
        if not proposals:
            messagebox.showinfo("Goi y", "Khong co goi y moi. Co the giam nguong de tim doi tuong mo; van can kiem tra cho bi sot.", parent=self.window)
            return
        self.remember()
        self.truth["origin"] = "manual_with_component_suggestions"
        self.truth["annotation_assistance"] = {"method":"threshold_8_connected_components", "threshold":threshold,
                                                "code":"src/eval/cell_proposals.py", "code_sha256":sha256(Path(__file__).with_name("cell_proposals.py"))}
        for proposal in proposals:
            item = object_from_box(proposal["bbox_xyxy"],len(self.truth["objects"])+1)
            item.update(annotation_method="threshold_component_suggestion",proposal_reviewed=False,
                        suggestion_threshold=proposal["threshold"],suggestion_flags=proposal["flags"],
                        suggested_bbox_xyxy=proposal["bbox_xyxy"])
            self.truth["objects"].append(item)
        self.redraw()
        self.next_suggestion()

    def next_suggestion(self):
        selected = self.items.curselection()
        start = selected[0]+1 if selected else 0
        order = list(range(start,len(self.truth["objects"])))+list(range(0,min(start,len(self.truth["objects"]))))
        for index in order:
            if self.is_pending(self.truth["objects"][index]):
                self.select_index(index,reveal=True)
                return

    def accept_selected(self):
        selected = self.items.curselection()
        if selected and selected[0]<len(self.truth["objects"]) and self.is_pending(self.truth["objects"][selected[0]]):
            self.remember()
            self.truth["objects"][selected[0]]["proposal_reviewed"] = True
            self.redraw()
            self.next_suggestion()

    def accept_visible(self):
        left,top = self.canvas.canvasx(0)/self.scale,self.canvas.canvasy(0)/self.scale
        right,bottom = left+self.canvas.winfo_width()/self.scale,top+self.canvas.winfo_height()/self.scale
        selected = [item for item in self.truth["objects"] if self.is_pending(item)
                    and left<=item["bbox_xyxy"][0] and top<=item["bbox_xyxy"][1]
                    and item["bbox_xyxy"][2]<=right and item["bbox_xyxy"][3]<=bottom]
        if selected:
            self.remember()
            for item in selected:
                item["proposal_reviewed"] = True
            self.redraw()

    def edit_selected(self):
        selected = self.items.curselection()
        if selected:
            self.edit_index=selected[0]
            self.status.set("Keo mot khung moi bao sat doi tuong dang chon de thay khung cu.")

    def undo(self):
        if self.history:
            self.truth = self.history.pop()
            self.truth.update(reviewed=False, status="DRAFT")
            self.dirty = True
            self.redraw()

    def delete_selected(self):
        selected = self.items.curselection()
        if not selected:
            return
        self.remember()
        index = selected[0]
        if index < len(self.truth["objects"]):
            self.truth["objects"].pop(index)
        else:
            self.truth["ignore_regions"].pop(index-len(self.truth["objects"]))
        self.redraw()

    def save(self, reviewed):
        candidate = copy.deepcopy(self.truth)
        candidate.update(reviewed=reviewed, reviewer=self.reviewer.get().strip(),
                         status="READY" if reviewed else "DRAFT")
        try:
            if sha256(self.path) != self.saved_file_digest:
                raise ValueError("File nhan da thay doi trong cua so khac. Luu/thoat cua so cu va mo lai de tranh mat nhan.")
            validate_cell_truth(candidate, "blob_05", self.raw, self.digest)
            previous = read_json(self.path)
            if previous != candidate:
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                write_json(self.path.parent/"history"/f"blob_05_{stamp}.json", previous)
            write_json(self.path, candidate, replace=True)
            self.saved_file_digest = sha256(self.path)
            overlay(self.raw, objects=candidate["objects"], ignores=candidate["ignore_regions"]).save(self.root/"data/gt/previews/blob_05_overlay.png")
        except (OSError, ValueError, KeyError) as error:
            messagebox.showerror("Chua luu duoc", str(error), parent=self.window)
            return False
        self.truth, self.dirty = candidate, False
        self.redraw()
        return True

    def save_draft(self):
        self.save(False)

    def complete(self):
        if self.save(True):
            messagebox.showinfo("Da luu nhan ra soat", "Chay lai prepare_ground_truth de cap nhat manifest va bang kiem ke. Chi danh dau khi da kiem tra toan bo anh.", parent=self.window)

    def close(self):
        if self.dirty and not messagebox.askyesno("Ban nhap chua luu", "Dong va bo cac thay doi chua luu?", parent=self.window):
            return
        self.window.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    if not (args.root/"data/gt/blob/blob_05.json").exists():
        parser.error("Run python -m src.eval.prepare_ground_truth first")
    window = tk.Tk()
    CellAnnotator(window, args.root.resolve())
    window.mainloop()


if __name__ == "__main__":
    main()
