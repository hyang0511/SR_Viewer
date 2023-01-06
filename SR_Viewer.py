import os
import math
import cv2
import numpy as np
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

def onMouse(event, x, y, flags, param):
    global mouse_y, mouse_x
    global canvas_ratio
    global box_min, box_max, box_step, box_size, obox_size
    if event == cv2.EVENT_MOUSEMOVE:
        mouse_y, mouse_x = y, x
    if event == cv2.EVENT_MOUSEWHEEL:
        if flags < 0:
            box_size = max(box_min, box_size - box_step)
        else:
            box_size = min(box_max, box_size + box_step)
        obox_size = int(box_size * canvas_ratio)

def scan_image(path, depth=0):
    file_list = []
    for file in os.listdir(path):
        if os.path.isfile('%s/%s' % (path, file)):
            ext = os.path.splitext(file)[-1].lower()
            if ext in ['.png', '.jpg', '.jpeg', '.bmp']:
                file_list.append('%s/%s' % (path, file))
        if os.path.isdir(os.path.join(path, file)):
            tmp_list = scan_image('%s/%s' % (path, file), depth+1)
            file_list.extend(tmp_list)
    if depth == 0:
        file_list.sort()
        for i in range(len(file_list)):
            file_list[i] = file_list[i].lstrip(path).lstrip('/')
    return file_list

def addText(image, text, color=(0, 0, 0)):
    global mask_size, font_size
    image_h, image_w, _ = image.shape
    image1 = image[:image_h - mask_size, :]
    image2 = image[image_h - mask_size:, :]
    mask = np.full_like(image2, fill_value=(255, 255, 255))
    image2 = cv2.addWeighted(image2, 0.4, mask, 0.6, 0.0)
    image2 = Image.fromarray(image2)
    font = ImageFont.truetype('FreeMono.ttf', font_size)
    draw = ImageDraw.Draw(image2)
    draw.text((image_w//2, mask_size//2), text, font=font, anchor='mm', fill=color, stroke_width=1)
    image = np.asarray(image)
    image = np.vstack((image1, image2))
    return image

def reset_interface():
    global image_list, image_h, image_w
    global canvas, canvas_h, canvas_w, canvas_image_w, canvas_ratio, canvas_y, canvas_x
    global box_min, box_max, box_step, box_size, obox_size
    global crop_index, crop_list, crop_size
    image_list = []
    for i in range(len(result_names)):
        image_list.append(cv2.imread('%s/%s' % (result_paths[i], image_names[image_index])))
    if aspect_ratio != 0:
        image_h, image_w, _ = image_list[main_index].shape
        crop_h, crop_w = int(min(image_h, image_w / aspect_ratio)), int(min(image_h * aspect_ratio, image_w))
        crop_y, crop_x = (image_h - crop_h) // 2, (image_w - crop_w) // 2
        for i in range(len(result_names)):
            image_list[i] = image_list[i][crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
    image_h, image_w, _ = image_list[main_index].shape
    crop_size = 1
    while True:
        canvas_h = (crop_size + pad_size) * (row_num * crop_num) - pad_size
        canvas_w = int(canvas_h * image_w / image_h) + (crop_size + pad_size) * col_num
        if canvas_h > win_h:
            crop_size -= 1
            canvas_h = (crop_size + pad_size) * (row_num * crop_num) - pad_size
            canvas_w = int(canvas_h * image_w / image_h) + (crop_size + pad_size) * col_num
            break
        if canvas_w > win_w:
            crop_size -= 1
            canvas_h = (crop_size + pad_size) * (row_num * crop_num) - pad_size
            canvas_w = win_w
            break
        crop_size += 1
    canvas_image_w = canvas_w - (crop_size + pad_size) * col_num
    canvas_y, canvas_x = (win_h - canvas_h) // 2, (win_w - canvas_w) // 2
    canvas_ratio = image_h / canvas_h
    canvas = np.full((win_h, win_w, 3), fill_value=pad_color, dtype='uint8')
    image = cv2.resize(image_list[main_index], (canvas_image_w, canvas_h), interpolation=cv2.INTER_CUBIC)
    canvas[canvas_y:canvas_y+canvas_h, canvas_x:canvas_x+canvas_image_w] = image
    box_min, box_max, box_step = int(min(canvas_h, canvas_image_w) * 0.05), min(canvas_h, canvas_image_w), int(min(canvas_h, canvas_image_w) * 0.01)
    box_size = int(min(canvas_h, canvas_image_w) * 0.1)
    obox_size = int(box_size * canvas_ratio)
    crop_index, crop_list = 0, [None for i in range(crop_num)]

# Main Configuration
result_names = ['hr', 'nearest', 'linear', 'area', 'cubic', 'lanczos']
result_paths = ['results/hr', 'results/nearest', 'results/linear', 'results/area', 'results/cubic', 'results/lanczos']
main_index = 0
crop_num = 5
row_num = 1
col_num = math.ceil(len(result_names) / row_num)

# Other Configuration
aspect_ratio = 0
crop_thickness = 2
crop_colors = [(0, 0, 220), (0, 220, 0), (255, 0, 0), (220, 0, 220), (0, 220, 220)]
pad_size = 3
pad_color = (0, 0, 0)
mask_size = 40
font_size = 35

# Scan Images
image_names = scan_image(result_paths[main_index])
for i in range(len(image_names)):
    for j in range(len(result_names)):
        if not os.path.exists('%s/%s' % (result_paths[j], image_names[i])):
            print('WARNING: Missing %s/%s' % (result_paths[j], image_names[i]))
            image_names[i] = None
            break
image_names = list(filter(lambda x:x is not None, image_names))

# Main UI Loop
cv2.namedWindow('SR Viewer', cv2.WINDOW_NORMAL)
cv2.setWindowProperty('SR Viewer', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.setMouseCallback('SR Viewer', onMouse)
_, _, win_w, win_h = cv2.getWindowImageRect('SR Viewer')
image_index = 0
mouse_y, mouse_x = 0, 0
reset_interface()
while True:
    tcanvas = canvas.copy()
    if crop_index < crop_num:
        box_y1, box_x1 = min(max(canvas_y, mouse_y - box_size // 2), canvas_y + canvas_h - box_size), min(max(canvas_x, mouse_x - box_size // 2), canvas_x + canvas_image_w - box_size)
        box_y2, box_x2 = box_y1 + box_size, box_x1 + box_size
        cv2.rectangle(tcanvas, (box_x1, box_y1), (box_x2, box_y2), crop_colors[crop_index], crop_thickness)
        obox_y1, obox_x1 = min(max(0, int((box_y1 - canvas_y) * canvas_ratio)), image_h - obox_size), min(max(0, int((box_x1 - canvas_x) * canvas_ratio)), image_w - obox_size)
        obox_y2, obox_x2 = obox_y1 + obox_size, obox_x1 + obox_size
        crop_list[crop_index] = (obox_y1, obox_x1, obox_y2, obox_x2)
        for i in range(len(image_list)):
            crop = image_list[i][obox_y1:obox_y2, obox_x1:obox_x2]
            crop_y, crop_x = i // col_num + crop_index * row_num, i % col_num
            crop_y, crop_x = (crop_size + pad_size) * crop_y + canvas_y, (crop_size + pad_size) * crop_x + pad_size + canvas_x + canvas_image_w
            crop = cv2.resize(crop, (crop_size, crop_size), interpolation=cv2.INTER_CUBIC)
            tcanvas[crop_y:crop_y+crop_size, crop_x:crop_x+crop_size] = crop
        ncanvas = tcanvas.copy()
        image = ncanvas[canvas_y:canvas_y+canvas_h, canvas_x:canvas_x+canvas_image_w]
        image = addText(image, image_names[image_index])
        ncanvas[canvas_y:canvas_y+canvas_h, canvas_x:canvas_x+canvas_image_w] = image
        for i in range(crop_index + 1):
            for j in range(len(image_list)):
                crop_y, crop_x = j // col_num + i * row_num, j % col_num
                crop_y, crop_x = (crop_size + pad_size) * crop_y + canvas_y, (crop_size + pad_size) * crop_x + pad_size + canvas_x + canvas_image_w
                crop = ncanvas[crop_y:crop_y+crop_size, crop_x:crop_x+crop_size]
                crop = addText(crop, result_names[j], crop_colors[i])
                ncanvas[crop_y:crop_y+crop_size, crop_x:crop_x+crop_size] = crop
    cv2.imshow('SR Viewer', ncanvas)

    key = cv2.waitKey(1)
    if key == ord('a'):
        image_index = (image_index + len(image_names) - 1) % len(image_names) 
        reset_interface()
    if key == ord('d'):
        image_index = (image_index + 1) % len(image_names) 
        reset_interface()
    if key == ord('s'):
        canvas = tcanvas
        crop_index += 1
        if crop_index == crop_num:
            image_name = os.path.splitext(image_names[image_index].replace('/', '_'))[0]
            crop_path = 'crops\%s_%s' % (image_name, datetime.now().strftime('%Y%m%d%H%M%S'))
            if not os.path.exists(crop_path):
                os.makedirs(crop_path, exist_ok=True)
            cv2.imwrite(os.path.join(crop_path, '%s.png' % image_name), tcanvas[canvas_y:canvas_y+canvas_h, canvas_x:canvas_x+canvas_w])
            cv2.imwrite(os.path.join(crop_path, '%s_.png' % image_name), ncanvas[canvas_y:canvas_y+canvas_h, canvas_x:canvas_x+canvas_w])
            for i in range(len(image_list)):
                cv2.imwrite(os.path.join(crop_path, '%s_%s.png' % (image_name, result_names[i])), image_list[i])
                for j in range(crop_num):
                    obox_y1, obox_x1, obox_y2, obox_x2 = crop_list[j]
                    crop = image_list[i][obox_y1:obox_y2, obox_x1:obox_x2]
                    cv2.imwrite(os.path.join(crop_path, '%s_%s_p%d.png' % (image_name, result_names[i], j+1)), crop)
    if key == ord('r'):
        reset_interface()
    if key == ord('q'):
        cv2.destroyAllWindows()
        break
