import os
import hashlib

import base64
import pathlib
import platform
import shutil
import stat
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

import cv2
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib import pagesizes
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from bioio import BioImage
from bioio_base.dimensions import Dimensions
from bioio_base.transforms import reshape_data
from tifffile import tifffile

from backend.constants import ReturnTypePath, FileType, BIT_DEPTH, Suffixes, CSP_CHANNEL_PREFIX, APP_DIR
from backend.expert_mode.event_manager import *
from backend.notifier import Notifier
from backend.settings import SettingsManager


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

    # sorting the Channel IDs
    for image_id in id_to_file:
        id_to_file[image_id] = dict(sorted(id_to_file[image_id].items()))
    # sorting the Image IDs
    id_to_file = dict(sorted(id_to_file.items()))

    return id_to_file


def load_directory(directory, channel_prefix=CSP_CHANNEL_PREFIX, mask_suffix=None,
                   return_type: ReturnTypePath = ReturnTypePath.BOTH_PATHS, event_manager: EventManager = None):
    assert directory is not None

    total_steps = 4 if return_type == ReturnTypePath.BOTH_PATHS else 3
    step = 0

    def notifier(process: str):
        nonlocal step
        step += 1
        if event_manager is not None:
            event_manager.notify(event=ProgressEvent(int(step / total_steps * 100), process=process))

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
            notifier("Organizing: Image Files")
            id_to_image = organize_files(tiff_files, channel_prefix=channel_prefix)
            notifier("Finished Organizing Files")
            return id_to_image
        case ReturnTypePath.MASK_PATHS:
            notifier("Organizing: Mask Files")
            mask_files = [path for path in file_paths if path.suffix == ".npy" and path.stem.endswith(mask_suffix)]
            id_to_mask = organize_files(mask_files, channel_prefix=channel_prefix, mask_suffix=mask_suffix)
            notifier("Finished Organizing Files")
            return id_to_mask
        case ReturnTypePath.BOTH_PATHS:
            notifier("Organizing: Image Files")
            id_to_image = organize_files(tiff_files, channel_prefix=channel_prefix)
            notifier("Organizing: Mask Files")
            mask_files = [path for path in file_paths if path.suffix == ".npy" and path.stem.endswith(mask_suffix)]
            id_to_mask = organize_files(mask_files, channel_prefix=channel_prefix, mask_suffix=mask_suffix)
            notifier("Finished Organizing Files!")
            return id_to_image, id_to_mask
    return None


class FileTransfer(Notifier):
    def __init__(self, file_types=None, event_manager: EventManager = None):
        super().__init__()
        self.file_types = file_types
        self.event_manager = event_manager

    def __call__(self, source_dir=None, target_dir=None,new_prefix=None,source_paths=None, *args, **kwargs):
        self._call_start_listeners(True)

        if source_dir is None and source_paths is None:
            raise ValueError("Either source_dir or source_paths must be provided.")
        if target_dir is None:
            raise ValueError("Target directory must be provided.")

        files_to_copy = source_paths
        if source_paths is None:
            file_filter = lambda file_path: file_path.is_file() and (
                True if self.file_types is None else file_path.suffix in self.file_types or file_path.suffix == ".npy")

            files = listdir(source_dir)
            files_to_copy = [file for file in files if file_filter(file)]

        target_dir.mkdir(parents=True, exist_ok=True)

        total_files = len(files_to_copy)
        copied_files = 0

        if self.event_manager is not None:
            self.event_manager.notify(event=ProgressEvent(0, process=f"Copy Files: {copied_files}/{total_files}"))

        n_files = len(files_to_copy)
        for iN, src_path in enumerate(files_to_copy):
            new_filename = src_path.name
            if new_prefix is not None and CSP_CHANNEL_PREFIX in new_filename:
                new_filename = new_filename.replace(CSP_CHANNEL_PREFIX, new_prefix, 1)

            target_path = target_dir / new_filename

            try:
                if target_path.exists():
                    if platform.system() == "Windows":
                        os.chmod(target_path, stat.S_IWRITE)
                    else:
                        target_path.chmod(0o777)
                    target_path.unlink()

                shutil.copy(str(src_path), str(target_path))

            except Exception as e:
                print(f"Something went wrong while processing {new_filename}: {str(e)}")
            finally:
                copied_files += 1
                if self.event_manager is not None:
                    self.event_manager.notify(event=ProgressEvent(int(copied_files / total_files * 100),
                                                                  process=f"Copy Files: {copied_files}/{total_files}"))

            if self.event_manager is None:
                kwargs = {"progress": str(int((iN + 1) / n_files * 100)) + "%",
                          "current_image": {"image_id": new_filename}}
                self._call_update_listeners(**kwargs)
            else:
                self.event_manager.notify(ProgressEvent(percent=int((iN + 1) / n_files * 100),
                                                        process=f"Exporting Images: {iN + 1}/{n_files} (Latest Image: {new_filename})"))

        self._call_completion_listeners()


def copy_files_between_directories(source_dir, target_dir, file_types=None, event_manager: EventManager = None):
    file_filter = lambda file_path: file_path.is_file() and (
        True if file_types is None else file_path.suffix in file_types)

    files = listdir(source_dir)
    files_to_copy = [file for file in files if file_filter(file)]

    total_files = len(files_to_copy)
    copied_files = 0

    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(0, process=f"Copy Files: {copied_files}/{total_files}"))

    n_files = len(files_to_copy)
    for iN, src_path in enumerate(files_to_copy):
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
            copied_files += 1
            if event_manager is not None:
                event_manager.notify(event=ProgressEvent(int(copied_files / total_files * 100),
                                                         process=f"Copy Files: {copied_files}/{total_files}"))

        if event_manager is None:
            # kwargs = {"progress": str(int((iN + 1) / n_images * 100)) + "%",
            #          "current_image": {"image_id": image_id}}
            # self._call_update_listeners(**kwargs)
            pass
        else:
            event_manager.notify(ProgressEvent(percent=int((iN + 1) / n_files * 100),
                                               process=f"Readout Images: {iN + 1}/{n_files} (Latest Image: {src_path.name})"))


def write_image_with_preprocessing(target_path, image_data):
    # TODO:PREPROCESSING (resize,dark corners,etc...)
    clean_data = np.squeeze(image_data)
    tifffile.imwrite(target_path, clean_data)


class CellSePiImage:

    def __init__(self, file_type, file_path, reader=None, *args, **kwargs):
        self._img = BioImage(file_path, reader=reader, *args, **kwargs)
        self._has_s = "S" in self._img.dims.order and self._img.dims.S > 1
        # print(f"Loaded image with dimensions: {self._img.dims.order} ({self._img.dims.C} channels, {self._img.dims.S} slices)")
        if "M" in self._img.dims.order:
            print(f"Warning: Image has M dimension, which is not supported.")
            raise Exception("Image has M dimension, which is not supported. (Mosaic or tiling images)")
        self._has_s = "S" in self._img.dims.order and self._img.dims.S > 1

        self.file_type = file_type

        self.bit_depths = self._infer_bit_depths()
        self.set_scene(self._img.current_scene)

        pass

    def _infer_bit_depths(self):
        bit_depths = []
        exception_occured = True
        try:
            match self.file_type:
                case FileType.LIF:  # The Lif reader often doesn't provide metadata in ome_metadata style, wherefore the proprietary xml element is used
                    bit_depths = []  # Currently no robust way of extracting bit depths from lif files available
                case FileType.CZI | FileType.ND2 | FileType.ND2_DIR | FileType.TIFF_DIR | FileType.OME_TIFF:
                    for img_meta in self._img.ome_metadata.images:
                        bit_depth = img_meta.pixels.significant_bits
                        bit_depths.append(bit_depth)
                case _:
                    raise TypeError(f"Unsupported file type: {self.file_type}")
            exception_occured = False
        except:
            print(f"Could not infer bit depth. Defaulting to container bit depth")
            exception_occured = True
            # raise TypeError(
            #    f"Could not infer bit depth. Defaulting to container bit depth (FileType: {self.file_type}).")

        if exception_occured or len(bit_depths) != len(self._img.scenes):
            for scene in self._img.scenes:
                self._img.set_scene(scene)
                bit_depth = np.iinfo(self._img.data.dtype).bits
                bit_depths.append(bit_depth)
            print(
                f"Could not infer bit depth. Defaulting to container bit depth(FileType: {self.file_type}). ({bit_depths})")

        bit_depths = np.array(bit_depths)
        assert np.all(bit_depths <= BIT_DEPTH), f"Bit depths must be <= {BIT_DEPTH} (found {np.max(bit_depths)})"

        return bit_depths

    @property
    def dims(self):
        """Returns a fresh Dimensions object reflecting the merged C and S."""
        d = self._img.dims
        if self._has_s:
            # Create a new Dimensions object from scratch.
            d = Dimensions(dims=["T", "C", "Z", "Y", "X"], shape=(d.T, d.C * d.S, d.Z, d.Y, d.X))
        return d

    @property
    def shape(self):
        """Returns the shape tuple matching the new dimensions (TCZYX)."""
        d = self.dims
        return (d.T, d.C, d.Z, d.Y, d.X)

    @property
    def xarray_data(self):
        xarray_data = self._img.xarray_data
        xarray_data = self.match_bit_depth(xarray_data)
        return xarray_data

    def set_scene(self, scene):
        self._img.set_scene(scene)
        # mask = np.array([s == scene for s in self._img.scenes])
        self.bit_depth = self.bit_depths[self._img.current_scene_index]

    @property
    def data(self):
        """Returns the 5D TCZYX array with S merged into C."""
        return self.get_image_data("TCZYX")

    def get_image_data(self, out_dims="TCZYX", **kwargs):
        """Retrieves data and automatically handles S-to-C merging."""
        if not self._has_s:  # We don't have to do anything in the default case
            original_img = self._img.get_image_data(out_dims, **kwargs)
            return self.match_bit_depth(original_img)

        # Force retrieve with S to perform the merge
        raw = self._img.get_image_data("TCZYXS", **kwargs)

        # Reshape: (T, C, Z, Y, X, S) -> (T, C, S, Z, Y, X) -> (T, C*S, Z, Y, X)
        # We move S next to C then flatten them
        t, c, z, y, x, s = raw.shape
        merged = raw.transpose(0, 1, 5, 2, 3, 4).reshape(t, c * s, z, y, x)

        # Change bit depth of data to default bit depth of 16 bit.
        merged = self.match_bit_depth(merged)

        return reshape_data(
            data=merged,
            given_dims="TCZYX",
            return_dims=out_dims
        )

    def get_stack(self, **kwargs: Any) -> np.ndarray:
        prev_scene = self._img.current_scene
        stack = []
        for scene in self._img.scenes:
            self.set_scene(scene)
            stack.append(self.data)

        self.set_scene(prev_scene)
        stack = np.stack(stack)
        return stack

    def match_bit_depth(self, data: np.array) -> np.array:
        """
        Adjusts the bit depth of the given data to match a pre-defined target bit depth and
        returns the transformed data. Works between 8 and 16 bit.

        Parameters:
        data : np.ndarray
            Input array whose bit depth is to be adjusted. Its elements are expected
            to conform to the original bit depth defined in the instance.

def load_image_to_numpy(path):
        Returns:
        np.ndarray
            A transformed array with the same shape as the input, but with its bit
            depth adjusted to the target defined by `BIT_DEPTH`.
        """
        arr16 = (data.astype(np.uint16) << (BIT_DEPTH - self.bit_depth)) | (
                data >> (2 * self.bit_depth - BIT_DEPTH)).astype(np.uint16)
        arr16 = arr16.astype(np.uint16)
        return arr16

    def __getattr__(self, name):
        """Delegate other common attributes to the internal BioImage object"""
        return getattr(self._img, name)


# def extract_bit_depth_from_lif(lif_img):
#     import xmltodict
#     import xml.etree.ElementTree as ET
#     # Convert metadata to dict
#     metadata = lif_img.metadata
#     xml_str = ET.tostring(metadata, encoding='unicode')
#     metadata_dict = xmltodict.parse(xml_str)
#
#     bit_depths = {}
#     for elem in metadata_dict["LMSDataContainerHeader"]["Element"]["Children"]["Element"]:
#         scene = elem["@Name"]
#         if "Image" in elem["Data"]:
#             attachment = \
#                 [attachment for attachment in elem["Data"]["Image"]["Attachment"] if
#                  attachment["@Name"] == "HardwareSetting"][0]
#         bit_depth = attachment["ATLConfocalSettingDefinition"]["@BitSize"]
#
#         bit_depths[scene] = int(bit_depth)
#
#     return bit_depths


def extract_from_file(
        file_type,
        path,
        target_dir,
        channel_prefix,
        event_manager: EventManager = None
):
    """
    Extracts all series from the provided file using the bioio library and
    copies the images to the target directory.
    Arguments:
          path {str} -- The path to the file.
          target_dir {str} -- The path to the target directory.
    """
    path = pathlib.Path(path)
    target_dir = pathlib.Path(target_dir)

    bio_image = CellSePiImage(file_type, path)

    # get all series in the lif file
    scenes = bio_image.scenes
    total_scenes = len(scenes)
    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(0, process=f"Extracting Series: {0}/{total_scenes}"))

    # Create the target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    for index, scene_id in enumerate(scenes):
        scene = scene_id

        # remove the unnecessary data in the array
        bio_image.set_scene(scene)
        # TCZXY 5D array
        raw_data = bio_image.data

        # get the amount of channels
        n_channels = raw_data.shape[1]
        if raw_data.shape[0] != 1:
            raise ValueError(f"CellSePi can't handle time series currently")

        for channel_id in range(n_channels):
            # Extract the height and width of the image
            image_data = raw_data[0, channel_id]

            # Construct file name and path
            file_name = f"{scene}{CSP_CHANNEL_PREFIX}{channel_id + 1}.tif"
            target_path = target_dir / file_name

            # Store 3D data to disk
            write_image_with_preprocessing(target_path, image_data)

        if event_manager is not None:
            event_manager.notify(event=ProgressEvent(int((index + 1) / total_scenes * 100),
                                                     process=f"Extracted Series: {index + 1}/{total_scenes}"))
    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(100, process=f"Finished extracting Series!"))


def extract_from_directory(
        file_type,
        path,
        target_dir,
        channel_prefix,
        event_manager: EventManager = None
):
    """
    Extracts all image scenes from the provided directory using the bioio library and
    copies the images to the target directory.
    Arguments:
          path {str} -- The path to the source directory.
          target_dir {str} -- The path to the target directory.
    """
    path = pathlib.Path(path)
    target_dir = pathlib.Path(target_dir)

    file_paths = listdir(path)

    image_paths = [fpath for fpath in file_paths if fpath.suffix.lower().replace(".", "") in file_type.value.extensions]
    mask_paths = [fpath for fpath in file_paths if fpath.suffix.lower().replace(".", "") in (
            Suffixes.SPOT_MASK.value.extensions + Suffixes.SEGMENTATION_MASK.value.extensions)]

    # File names are of the format <scene><channel_prefix><channel_id>.tif
    # and bioio returns a T x C x Z x Y x X image with T=1 and C=1
    channels_in_individual_files = all([channel_prefix in str(ipath) for ipath in image_paths])

    smallest_channel_id = 1
    if channels_in_individual_files:
        channel_ids = [int(fpath.stem.split(channel_prefix)[1]) for fpath in image_paths]
        smallest_channel_id = min(channel_ids)

    scenes = defaultdict(list)
    scenes_masks = defaultdict(list)
    for ipath in image_paths:
        stem = ipath.stem
        scene = stem
        channel = smallest_channel_id
        if channels_in_individual_files:
            scene, channel = stem.split(channel_prefix)
        channel_id = int(channel) - smallest_channel_id + 1
        scenes[scene].append((channel_id, ipath))
        # cur_mask_paths = [mpath for mpath in mask_paths if mpath.stem.split(channel_prefix)[0] == scene]
        for mpath in mask_paths:
            stem = mpath.stem
            scene_mask, channel_mask = stem.split(channel_prefix)
            # channel_id_mask = int(channel_mask)
            if scene_mask != scene:  # Make sure that scene matches
                continue
            if str(channel_id) not in channel_mask:  # Make sure that channel matches
                continue
            scenes_masks[scene].append((channel_id, mpath))

    # scenes = bio_image.scenes
    total_scenes = len(scenes)
    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(0, process=f"Extracting Directory: {0}/{total_scenes}"))

    # Create the target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)

    for iX, scene in enumerate(scenes):

        if channels_in_individual_files:
            raw_data = []
            for channel_id, fpath in sorted(scenes[scene], key=lambda elem: elem[1]):
                # TCZXY 5D array
                bio_image = CellSePiImage(file_type, fpath)
                c_raw_data = bio_image.data
                raw_data.append(c_raw_data)
            raw_data = np.concat(raw_data, axis=1)
        else:
            channel_id, fpath = scenes[scene][0]
            bio_image = CellSePiImage(file_type, fpath)
            raw_data = bio_image.data

        if raw_data.shape[0] != 1:
            raise ValueError(f"CellSePi can't handle time series currently")

        n_channels = raw_data.shape[1]
        for channel_id in range(n_channels):
            image_data = raw_data[0, channel_id]

            # Construct file name and path
            file_name = f"{scene}{CSP_CHANNEL_PREFIX}{channel_id}.tiff"
            target_path = target_dir / file_name

            # Store 3D data to disk
            write_image_with_preprocessing(target_path, image_data)

        for channel_id, mpath in scenes_masks[scene]:
            # Copy all associated mask information
            src_path = mpath
            target_path = target_dir / f"{scene}{CSP_CHANNEL_PREFIX}{mpath.stem.split(channel_prefix)[1]}.npy"
            shutil.copy(str(src_path), str(target_path))

        if event_manager is not None:
            event_manager.notify(event=ProgressEvent(int((iX + 1) / total_scenes * 100),
                                                     process=f"Extracted Series: {iX + 1}/{total_scenes}"))
    if event_manager is not None:
        event_manager.notify(
            event=ProgressEvent(100, process=f"Finished extracting Series!"))


def remove_gradient(img):
    """
    The method evens out the background of the images to prone microscopy errors

    Arguments:
        img {PIL.Image} -- The image to be corrected

    """
    # ToDo EK: Currently not used and likely not compatible to recent version. Optionally to adapt to new version and allow user based application, or just provide in expert mode as module.

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


def process_channel(channel_id, channel_path):
    image = tifffile.imread(channel_path)
    if image.ndim == 3:
        image = np.max(image, axis=0)

    h, w = image.shape[:2]

    max_size = 150
    scale = max_size / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    down_scaled_image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    image_8bit = cv2.convertScaleAbs(down_scaled_image, alpha=1 / 256.0)
    _, buffer = cv2.imencode('.png', image_8bit, [cv2.IMWRITE_PNG_COMPRESSION, 1])

    return channel_id, base64.b64encode(buffer).decode('utf-8')


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


def consistent_hash(data):
    data_bytes = data.encode('utf-8')
    c_hash = hashlib.sha256(data_bytes).hexdigest()
    return c_hash


def export_dataframe_to_pdf(df: pd.DataFrame, output_path: str):
    # Setup document geometry (Standard Letter size)
    doc = SimpleDocTemplate(output_path, pagesize=pagesizes.A4, rightMargin=30, leftMargin=30, topMargin=30,
                            bottomMargin=30)
    story = []

    # Add a title header
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    story.append(Paragraph("Fluorescence Values", title_style))
    story.append(Spacer(1, 15))  # 15 point vertical spacing

    # Prepare data matrix: Include headers + all row values
    # if no mask was detected pdf with
    if df.empty or len(df.columns) == 0:
        data_matrix = [["No mask was generated"]]
    else:
        data_matrix = [df.columns.to_list()] + df.values.tolist()

    # Create the ReportLab dynamic Table widget
    pdf_table = Table(data_matrix)

    # Apply a clean, modern aesthetic theme (JetBrains-style dark/light structure)
    pdf_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1A73E8")),  # Primary header color
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        # Zebra striping for structural readability
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F8F9FA")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]))

    story.append(pdf_table)
    doc.build(story)


def load_image_to_numpy(path):
    im = tifffile.imread(path)
    array = np.array(im)
    return array


class DirectoryManager:
    """
    Manages project directories and intermediate file storage.
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, app_dir=None):
        if app_dir is None:
            app_dir = APP_DIR
        self._base_path = Path(app_dir)
        self._cache_path: Optional[Path] = None

    @property
    def base_directory(self) -> Path:
        return self._base_path

    @property
    def cache_directory(self) -> Path:
        """
        Returns the path for intermediate files, creating it if it doesn't exist.
        """
        if self._cache_path is None:
            self._cache_path = self._base_path / "cache"
            self._cache_path.mkdir(parents=True, exist_ok=True)

        return self._cache_path

    def get_cache_file_path(self, filename: str) -> Path:
        """
        Returns a full path for a file within the intermediate directory.
        """
        # Accessing the property ensures the directory is created
        dir_path = Path(self.cache_directory.path)
        return dir_path / filename

    def get_cache_dir_path(self, dirname: str, makedir=True) -> Path:
        dirpath = self.cache_directory / dirname

        if makedir:
            os.makedirs(dirpath, exist_ok=True)
        return dirpath

    def streamline_cache(self):
        """
        Removes only the old entries in the cache directory.
        Keeps the three most recent directories.
        """
        if self.cache_directory and self.cache_directory.exists():
            modification_times = []
            for item in self._cache_path.glob("*"):
                if item.is_dir():
                    modification_times.append([item, item.stat().st_mtime])

            print(modification_times)
            modification_times = sorted(modification_times, key=lambda elem: elem[1], reverse=True)
            for elem in modification_times[SettingsManager().settings.cache.cutoff:]:
                item = elem[0]
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

            pass

    def clear_cache(self):
        """
        Removes all files in the cache directory.
        """
        if self.cache_directory and self.cache_directory.exists():
            for item in self._cache_path.glob("*"):

                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()

