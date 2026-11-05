"""Unverified box suggestions for human annotation, independent of the LoG core.

Histogram threshold + 8-connected components, implemented with NumPy/Python.
These proposals are not reference labels until a person checks them.
"""

import numpy as np


def otsu_threshold(image):
    histogram = np.bincount(image.ravel(), minlength=256).astype(np.float64)
    weight = np.cumsum(histogram)
    moment = np.cumsum(histogram * np.arange(256))
    valid = (weight > 0) & (weight < weight[-1])
    score = np.full(256, -1., dtype=np.float64)
    score[valid] = ((moment[-1]*weight[valid] - moment[valid]*weight[-1])**2
                    / (weight[valid]*(weight[-1]-weight[valid])))
    return int(np.argmax(score))


def overlaps_existing(box, existing, ignores):
    x0, y0, x1, y1 = box
    cx, cy = (x0+x1)/2, (y0+y1)/2
    for item in existing:
        bx0, by0, bx1, by1 = item["bbox_xyxy"]
        if ((x0 <= item["x"] <= x1 and y0 <= item["y"] <= y1)
                or (bx0 <= cx <= bx1 and by0 <= cy <= by1)):
            return True
        intersection = max(0, min(x1,bx1)-max(x0,bx0))*max(0,min(y1,by1)-max(y0,by0))
        union = (x1-x0)*(y1-y0)+(bx1-bx0)*(by1-by0)-intersection
        if intersection > 0 and intersection/union > .15:
            return True
    return any(max(x0,b[0]) < min(x1,b[2]) and max(y0,b[1]) < min(y1,b[3]) for b in ignores)


def propose_boxes(image, existing=(), ignores=(), threshold=None, min_area=18, max_area=1600):
    """Return added boxes only; never edit/replace existing annotations."""
    image = np.asarray(image)
    if image.ndim != 2 or image.dtype != np.uint8:
        raise ValueError("Suggestions require grayscale uint8 input")
    if threshold is None:
        threshold = max(1, round(.85*otsu_threshold(image)))
    if not isinstance(threshold, (int, np.integer)) or not 1 <= threshold <= 254:
        raise ValueError("Suggestion threshold must be an integer from 1 to 254")
    height, width = image.shape
    foreground = image > threshold
    visited = np.zeros(image.shape, dtype=bool)
    boxes = []
    for sy, sx in zip(*np.nonzero(foreground)):
        if visited[sy, sx]:
            continue
        visited[sy, sx] = True
        stack = [(int(sy), int(sx))]
        area, x0, x1, y0, y1 = 0, sx, sx, sy, sy
        while stack:
            y, x = stack.pop()
            area += 1
            x0, x1, y0, y1 = min(x0,x), max(x1,x), min(y0,y), max(y1,y)
            for ny in range(max(0,y-1), min(height,y+2)):
                for nx in range(max(0,x-1), min(width,x+2)):
                    if foreground[ny,nx] and not visited[ny,nx]:
                        visited[ny,nx] = True
                        stack.append((ny,nx))
        if (not min_area <= area <= max_area or min(x0,y0) <= 1
                or x1 >= width-2 or y1 >= height-2 or x1-x0 < 2 or y1-y0 < 2):
            continue
        box = [float(x0-1), float(y0-1), float(x1+1), float(y1+1)]
        if overlaps_existing(box, existing, ignores):
            continue
        bw, bh = box[2]-box[0], box[3]-box[1]
        flags = []
        if max(bw,bh)/min(bw,bh) > 1.8 or area > 260:
            flags.append("possible_touching_or_elongated_objects")
        if area/(bw*bh) < .35:
            flags.append("irregular_component")
        boxes.append({"bbox_xyxy": box, "threshold": int(threshold),
                      "area": area, "flags": flags})
    return boxes
