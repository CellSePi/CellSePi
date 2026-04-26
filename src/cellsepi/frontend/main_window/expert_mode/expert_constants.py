import math
import platform
from enum import Enum
import flet as ft

from cellsepi.backend.main_window.expert_mode.modules.image_readout import ImageReadoutModule
from cellsepi.backend.main_window.expert_mode.modules.image_segmentation import ImageSegmentationModule
from cellsepi.backend.main_window.expert_mode.modules.project_3d_to_2d import Project3dTo2d
from cellsepi.backend.main_window.expert_mode.modules.read_lif import ReadLif
from cellsepi.backend.main_window.expert_mode.modules.read_tif import ReadTif
from cellsepi.backend.main_window.expert_mode.modules.review import Review
from cellsepi.backend.main_window.expert_mode.modules.spot_detection import SpotDetectionModule

#Constants used in the PipelineBuildingTool(ExpertMode)
CANVAS_HEIGHT = 10000
CANVAS_WIDTH = 10000
MODULE_WIDTH = 235
MODULE_HEIGHT = 80
SPACING_X = 10
SPACING_Y = 20
SHOWROOM_PADDING_X = 20
SHOWROOM_MODULE_COUNT = 4
ARROW_LENGTH = 23
ARROW_ANGLE = math.radians(40)
ARROW_PADDING = -1
ARROW_COLOR = ft.Colors.CYAN_900
INVALID_COLOR = ft.Colors.BLACK54
VALID_COLOR = ft.Colors.WHITE30
MENU_COLOR = ft.Colors.BLACK54
DISABLED_BUTTONS_COLOR = ft.Colors.BLACK12
USER_OPTIONS_LIMIT = 9
ZOOM_VALUE = 0.20
BOTTOM_SPACING = 20
MAIN_ACTIVE_COLOR = ft.Colors.WHITE60
THROTTLE_UPDATE_LINES = 0.036 #~30FPS
DEBUG = False

class ModuleType(Enum):
    """
    Enum for all Modules.
    Register new Modules here!
    """
    IMAGE_READOUT = ImageReadoutModule
    IMAGE_SEGMENTATION = ImageSegmentationModule
    SPOT_DETECTION = SpotDetectionModule
    READ_LIF = ReadLif
    READ_TIF = ReadTif
    PROJECTION_3D_TO_2D = Project3dTo2d
    REVIEW = Review


