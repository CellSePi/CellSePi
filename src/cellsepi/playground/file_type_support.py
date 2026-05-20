import os.path

from backend.main_window.constants import FileType
from backend.main_window.data_util import CellSePiImage

if __name__ == '__main__':
    nd2_path = "/Users/erik/Downloads/CellSePi Segmentation Data/ND2_Test_Images/GFP001.nd2"
    czi_path = "/Users/erik/Downloads/CellSePi Segmentation Data/Zeiss_Test_Images/Tumor_HE_Orig_small.czi"
    lif_path = "/Users/erik/Documents/Promotion/Projekte/Anjas_Stuff/_data/Segmentation Training Data/28-06-2024/HEK293_CellMaskDR_LessDense_01.lif"
    lif_path = "/Users/erik/Downloads/CellSePi Segmentation Data/smFISH Confocal/02-04-2025_A498_DAPI_488-LINC01116_546-SERPINE1_647-TM4SF1_01.lif"

    paths = [lif_path, nd2_path, czi_path]
    # paths = [lif_path]

    for path in paths:
        match os.path.splitext(path)[1]:
            case ".nd2":
                file_type = FileType.ND2
            case ".czi":
                file_type = FileType.CZI
            case ".lif":
                file_type = FileType.LIF
            case _:
                raise Exception(f"File type not supported: {path}")

        img = CellSePiImage(file_type, path)
        data = img.data

        stack = img.get_stack()

        pass