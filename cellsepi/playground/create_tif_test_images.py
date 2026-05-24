import numpy as np
import tifffile
import cv2
import os


def create_test_image(folder, name, width, height, label):
    os.makedirs(folder, exist_ok=True)
    filename = os.path.join(folder, f"{name}.tif")

    z = 5
    image_3d = np.zeros((z, height, width), dtype=np.uint16)

    image_3d[0] = np.random.randint(0, 65535, (height, width), dtype=np.uint16)

    step = max(width, height) // 15
    grid = np.zeros((height, width), dtype=np.uint16)
    for i in range(0, max(width, height), step):
        cv2.line(grid, (i, 0), (i, height), 65535, 2)
        cv2.line(grid, (0, i), (width, i), 65535, 2)
    image_3d[1] = grid

    for i in range(4):
        val = (i + 1) * 16000
        cv2.rectangle(image_3d[2], (i * width // 4, i * height // 4),
                      ((i + 1) * width // 4, (i + 1) * height // 4), val, -1)

    cv2.putText(image_3d[4], label, (100, height // 2),
                cv2.FONT_HERSHEY_SIMPLEX, width / 1000, 65535, 8)

    tifffile.imwrite(filename, image_3d, imagej=True, metadata={'axes': 'ZYX'})
    print(f"Saved: {filename} ({width}x{height})")


resolutions = {
    "FullHD": (1920, 1080),
    "2K": (2048, 1080),
    "4K": (3840, 2160),
    "8K": (7680, 4320)
}

output_folder = "test_images"

for res_name, (w, h) in resolutions.items():
    create_test_image(output_folder, f"test_{res_name}_horiz_c2", w, h, f"{res_name} Horiz")
    create_test_image(output_folder, f"test_{res_name}_vert_c2", h, w, f"{res_name} Vert")

print(f"\nAlle Test images are created in the folder:'{output_folder}/'")