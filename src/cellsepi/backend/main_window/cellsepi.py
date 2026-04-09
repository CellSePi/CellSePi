from cellsepi.backend.main_window.config_file import ConfigFile


class CellSePi:
    def __init__(self):
        super().__init__()
        self.config: ConfigFile = ConfigFile()
        self.segmentation_running = False
        self.segmentation_thread = None
        self.training_running = False
        self.model_path = None
        self.re_train_model_path=None
        self.readout_running = False
        self.readout_thread = None
        self.readout_path = None
        self.linux_or_3d = False

        self.image_id = None
        self.channel_id = None
        self.current_channel_prefix = None
        self.current_mask_suffix = None

        self.readout = None

        self.adjusted_image_path = None
        self.image_paths = None #[image_id, different images sorted by channel]
        self.linux_images = None #[image_id][channel_id] = base64 png image
        self.mask_paths = None
        self.working_directory = None

