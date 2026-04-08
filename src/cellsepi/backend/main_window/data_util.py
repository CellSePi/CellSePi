import base64
import os
import pathlib
import platform
import shutil
import stat
from concurrent.futures import ThreadPoolExecutor
from enum import Enum, auto
from io import BytesIO

import numpy as np
from PIL import Image
from bioio import BioImage
import bioio_lif
from tifffile import tifffile

from cellsepi.backend.main_window.expert_mode.event_manager import *


def listdir(directory):
    dir_list = [directory / elem for elem in os.listdir(directory)]
    return dir_list


def organize_files(files, channel_prefix, mask_suffix=""):
    id_to_file = {}
    for file in files:

        if channel_prefix in file.name:
            image_id, channel_id = file.stem.replace(mask_suffix, "").split(channel_prefix)
            if image_id not in id_to_file:
                id_to_file[image_id] = {}

            if channel_id in id_to_file[image_id]:
                raise Exception(
                    f"""The directory already includes a file with the same image and channel ids.
                                Image Id: {image_id}
                                Channel Id: {channel_id}
                                Path: {file}""")

            id_to_file[image_id][channel_id] = str(file)

    #sorting the Channel IDs
    for image_id in id_to_file:
        id_to_file[image_id] = dict(sorted(id_to_file[image_id].items()))
    #sorting the Image IDs
    id_to_file = dict(sorted(id_to_file.items()))

    return id_to_file

class ReturnTypePath(Enum):
    IMAGE_PATHS = auto()
    MASK_PATHS = auto()
    BOTH_PATHS = auto()

def load_directory(directory, channel_prefix=None, mask_suffix=None,return_type: ReturnTypePath=ReturnTypePath.BOTH_PATHS,event_manager: EventManager=None):
    assert directory is not None

    total_steps = 4 if return_type == ReturnTypePath.BOTH_PATHS else 3
    step = 0

    def notifier(process:str):
        nonlocal step
        step += 1
        if event_manager is not None:
            event_manager.notify(event=ProgressEvent(int(step/total_steps*100), process=process))

    if channel_prefix is None:
        channel_prefix = "c"

    if mask_suffix is None:
        mask_suffix = "_seg"

    if event_manager is not None:
        event_manager.notify(event=ProgressEvent(0, process="Organizing: Listing Directory"))

    names = os.listdir(directory)
    paths = [directory / name for name in names]
    file_paths = [path for path in paths if path.is_file()]


    notifier("Organizing: Filtering Directory for Images")
    tiff_files = [path for path in file_paths if path.suffix == ".tif" or path.suffix == ".tiff"]

    match return_type:
            case ReturnTypePath.IMAGE_PATHS:
                notifier( "Organizing: Image Files")
                id_to_image = organize_files(tiff_files, channel_prefix=channel_prefix)
                notifier( "Finished Organizing Files")
                return id_to_image
            case ReturnTypePath.MASK_PATHS:
                notifier( "Organizing: Mask Files")
                mask_files = [path for path in file_paths if path.suffix == ".npy" and path.stem.endswith(mask_suffix)]
                id_to_mask = organize_files(mask_files, channel_prefix=channel_prefix, mask_suffix=mask_suffix)
                notifier( "Finished Organizing Files")
                return id_to_mask
            case ReturnTypePath.BOTH_PATHS:
                notifier( "Organizing: Image Files")
                id_to_image = organize_files(tiff_files, channel_prefix=channel_prefix)
                notifier( "Organizing: Mask Files")
                mask_files = [path for path in file_paths if path.suffix == ".npy" and path.stem.endswith(mask_suffix)]
                id_to_mask = organize_files(mask_files, channel_prefix=channel_prefix, mask_suffix=mask_suffix)
                notifier( "Finished Organizing Files!")
                return id_to_image, id_to_mask
    return None

def copy_files_between_directories(source_dir, target_dir, file_types = None, event_manager: EventManager=None):
    file_filter = lambda file_path: file_path.is_file() and (True if file_types is None else file_path.suffix in file_types)


    files = listdir(source_dir)
    files_to_copy = [file for file in files if file_filter(file)]

    total_files = len(files_to_copy)
    copied_files = 0

    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(0, process=f"Copy Files: {copied_files}/{total_files}"))
    for src_path in files_to_copy:
        target_path = target_dir / src_path.name

        try:
            if target_path.exists():
                if platform.system() == "Windows":
                    os.chmod(target_path, stat.S_IWRITE)
                else:
                    target_path.chmod(0o777)
                target_path.unlink()

            shutil.copy(str(src_path), str(target_path))

        except Exception as e:
            print(f"Something went wrong while processing {src_path.name}: {str(e)}")
        finally:
            copied_files+=1
            if event_manager is not None:
                event_manager.notify(event=ProgressEvent(int(copied_files/total_files*100), process=f"Copy Files: {copied_files}/{total_files}"))

    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(100, process="Finished copy Files!"))

def load_lif3d_bioimage(lif3d_path):
    lif3d_path = pathlib.Path(lif3d_path)
    # See Readme at https://github.com/bioio-devs/bioio
    bio_img = BioImage(lif3d_path)

    # test_data = np.squeeze(bio_img.get_stack(), axis=1)
    images = []
    series_ids = []
    for scene in bio_img.scenes:
        bio_img.set_scene(scene)
        cur_data = bio_img.data
        shape = cur_data.shape

        if shape[-1] != 1024 or shape[-2] != 1024:
            # Special case of a single series in a .lif file having a resolution of 512 x 512
            continue

        cur_data = cur_data.reshape((shape[0], -1, shape[-2], shape[-1])).reshape(shape[0], shape[2], shape[1],
                                                                                  shape[-2], shape[-1])
        shape = cur_data.shape
        series_ids.append(scene)
        images.append(cur_data)
        # fig, axes = plt.subplots(ncols=shape[2], nrows=shape[1], sharex=True, sharey=True)
        # for iR in range(shape[1]):
        #    for iC in range(shape[2]):
        #        axes[iR, iC].imshow(test_data[0, iR, iC])
        # plt.tight_layout()
        # plt.show()
    images = np.stack(images)
    images = np.squeeze(images)
    return series_ids, images


def extract_from_lif3d_file(lif3d_path, target_dir, channel_prefix, event_manager: EventManager = None):
    series_ids, images = load_lif3d_bioimage(lif3d_path)

    images = np.transpose(images, axes=(0, 2, 3, 4, 1))
    target_dir = pathlib.Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    total_scenes = len(series_ids)
    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(0, process=f"Extracting Series: {0}/{total_scenes}"))
    for s_idx, series in enumerate(images):
        series_id = series_ids[s_idx]
        for c_idx, channel_3d in enumerate(series):
            file_name = f"{series_id}{channel_prefix}{c_idx + 1}.tif"
            target_path = target_dir / file_name
            tifffile.imwrite(target_path, channel_3d)
        if event_manager is not None:
            event_manager.notify(event=ProgressEvent(int((s_idx + 1) / total_scenes * 100),
                                                     process=f"Extracted Series: {s_idx + 1}/{total_scenes}"))
    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(100, process=f"Finished extracting Series!"))


def extract_from_lif_file(lif_path, target_dir,channel_prefix,event_manager: EventManager=None):
    """
    Extracts all series from the lif file using the bioio-lif library and
    copies the images to the target directory.
    Arguments:
          lif_path {str} -- The path to the lif file.
          target_dir {str} -- The path to the target directory.
    """

    lif_path = pathlib.Path(lif_path)
    target_dir = pathlib.Path(target_dir)
    if lif_path.suffix == ".lif":
        bio_image = BioImage(lif_path,reader=bioio_lif.Reader)  # Specify the backend explicitly
        data = np.squeeze(bio_image.data)
        is_3d = (data.ndim >= 4 and data.shape[1] > 1)

        if is_3d:
            extract_from_lif3d_file(lif_path, target_dir, channel_prefix, event_manager)
            return

        # Create the target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # get all series in the lif file
        scenes= bio_image.scenes
        total_scenes = len(scenes)
        if event_manager is not None:
            event_manager.notify(
                event=ProgressEvent(0, process=f"Extracting Series: {0}/{total_scenes}"))

        for index,scene_id in enumerate(scenes):
            scene= scene_id

            #remove the unnecessary data in the array
            bio_image.set_scene(scene)
            #TCZXY 5D array
            npy_array= bio_image.data
            squeezed_img= np.squeeze(npy_array)

            #get the amount of channels
            n_channels = squeezed_img.shape[0]

            for channel_id in range(n_channels):
                # Extract the height and width of the image
                image= squeezed_img[channel_id]
                img = Image.fromarray(image)#doesnt work

                # Construct file name and path
                file_name = f"{scene}{channel_prefix}{channel_id + 1}.tif"
                target_path = target_dir / file_name

                try:
                    # Handle existing files
                    if target_path.exists():
                        if platform.system() == "Windows":
                            os.chmod(target_path, stat.S_IWRITE)  # Set writable on Windows
                        else:
                            target_path.chmod(0o777)  # Set writable on Unix
                        target_path.unlink()  # Remove the existing file

                    # Save the image to the target path using pillows save function
                    img.save(str(target_path))

                except Exception as e:
                    print(f"Error processing {file_name}: {e}")
                    continue
            if event_manager is not None:
                event_manager.notify(event=ProgressEvent(int((index+1) / total_scenes * 100),
                                                         process=f"Extracted Series: {index+1}/{total_scenes}"))
        if event_manager is not None:
            event_manager.notify(
                event=ProgressEvent(100, process=f"Finished extracting Series!"))





def load_image_to_numpy(path):
    im = tifffile.imread(path)
    array = np.array(im)
    return array


def write_numpy_to_image(array, path):
    im = Image.fromarray(array)
    im.save(path)
    pass


def remove_gradient(img):

    """
    The method evens out the background of the images to prone microscopy errors

    Arguments:
        img {PIL.Image} -- The image to be corrected

    """
    top = np.median(img[100:200, 400: -400])
    bottom = np.median(img[-200:-100, 400: -400])

    left = np.median(img[400:-400, 100: 200])
    right = np.median(img[400:-400, -200: -100])

    median = np.median(img[200:-200, 200:-200])

    max_val = np.max([top, bottom, left, right])

    row_count = img.shape[0]

    X = np.arange(row_count) / (row_count - 1)
    b = bottom
    a = top - bottom
    Y_v = a * X + b
    Y_v -= median

    b = right
    a = left - right
    Y_h = a * X + b
    Y_h -= median

    correction_v = np.tile(Y_v, (row_count, 1)).transpose()
    correction_h = np.tile(Y_h, (row_count, 1))
    correction = correction_h + correction_v

    corrected_img = img + correction
    return corrected_img


def transform_image_path(image_path, output_path):
    """
    This method converts images with bit depth of 16 bit to 8 bit

    Attributes:
        image_path (pathlib.Path): Path to the image
        output_path (pathlib.Path): Path where to save the converted image

    Returns:
        True if the image was converted successfully
        False if the image was not converted because it had an incompatible format
    """
    with Image.open(image_path) as img:
        # convert to 8 bit if necessary
        if img.mode == "I;16":
            array16 = np.array(img, dtype=np.uint16)
            array8 = (array16 / 256).astype(np.uint8)
            img8 = Image.fromarray(array8)
            img8.save(output_path, format="TIFF")
            return True
        elif img.mode in ["L", "RGB", "P", "RGBA"]:
            return True
        else:
            return False


def process_channel(channel_id, channel_path):
    image = tifffile.imread(channel_path)
    if image.ndim == 3:
        image = np.max(image, axis=2)
    img = Image.fromarray(image)
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return channel_id, base64.b64encode(buffer.getvalue()).decode('utf-8')

def convert_series_parallel(image_id, cur_image_paths):
    png_images = {image_id: {}}
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(process_channel, channel_id, cur_image_paths[channel_id]): channel_id
            for channel_id in cur_image_paths
        }
        for future in futures:
            channel_id, encoded_image = future.result()
            png_images[image_id][channel_id] = encoded_image

    return png_images

def convert_tiffs_to_png_parallel(image_paths):
    """
    Converts a dict of tiff images to png images using multiprocessing.

    Args:
        image_paths (dict): the dict of image paths of tiff images
    """
    if image_paths is not None:
        png_images = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(convert_series_parallel, image_id, image_paths[image_id]): image_id
                for image_id in image_paths
            }
            for future in futures:
                result = future.result()
                png_images.update(result)

        return png_images
    else:
        return None

def convert_tiffs_to_png(image_paths):
    """
    Converts a dict of tiff images to png images.

    Args:
        image_paths (dict): the dict of image paths of tiff images
    """
    if image_paths is not None:
        png_images = {}
        for image_id in image_paths:
            cur_image_paths = image_paths[image_id]
            if image_id not in png_images:
                png_images[image_id] = {}
            for channel_id in cur_image_paths:
                image = image = Image.open(cur_image_paths[channel_id])

                buffer = BytesIO()
                image.save(buffer, format="PNG")
                buffer.seek(0)

                png_images[image_id][channel_id] = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return png_images
    else:
        return None