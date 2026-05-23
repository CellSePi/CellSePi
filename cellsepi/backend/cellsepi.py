from backend.config_file import ConfigFile
from backend.constants import APP_DIR
from images import BatchImageSegmentation


class CellSePi:
    def __init__(self):
        super().__init__()
        self.app_dir, self.models_dir, self.plugins_dir = self.createDirectory()
        self.config: ConfigFile = ConfigFile(self.app_dir)
        self.segmentation_running = False
        self.segmentation_thread = None
        self.training_running = False
        self.model_path = None
        self.model_type = None  # Options are: "CustomV3", "CustomV4", "Cellpose", "CellposeSAM"
        self.re_train_model_path = None
        self.readout_running = False
        self.readout_thread = None
        self.readout_path = None

        self.image_id = None
        self.channel_id = None
        self.current_channel_prefix = None
        self.current_mask_suffix = None


        self.readout = None

        self.adjusted_image_path = None
        self.image_paths = None  # [image_id, different images sorted by channel]
        self.linux_images = None  # [image_id][channel_id] = base64 png image
        self.mask_paths = None
        self.working_directory = None

    @property
    def gpu(self) -> bool:
        return BatchImageSegmentation.GPU

    @gpu.setter
    def gpu(self, value: bool):
        BatchImageSegmentation.GPU = value

    def createDirectory(self):
        app_dir = APP_DIR
        app_dir.mkdir(parents=True, exist_ok=True)
        models_dir = app_dir / "models"
        plugins_dir = app_dir / "plugins"
        models_dir.mkdir(parents=True, exist_ok=True)
        plugins_dir.mkdir(parents=True, exist_ok=True)
        return app_dir, models_dir, plugins_dir
