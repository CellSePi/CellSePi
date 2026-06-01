import os
from PIL import Image

folder_path = r""

sizes = [256, 128, 64, 48, 32, 24, 16]
images = []


for size in sizes:
    filename = os.path.join(folder_path, f"icon_{size}.png")

    if os.path.exists(filename):
        img = Image.open(filename)
        images.append(img)
        print(f"[OK] {filename} loadet.")
    else:
        print(f"[-] {filename} not found (skipped).")

if images:
    base_image = images[0]
    additional_images = images[1:]

    output_name = "icon_windows.ico"

    base_image.save(
        output_name,
        format="ICO",
        append_images=additional_images
    )

    print(f"\nSuccess! '{output_name}' was successfully build with {len(images)} slices.")
else:
    print("\nError: No icons found.")