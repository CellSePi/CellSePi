[start:subclass]
from backend.expert_mode.module import *

class MyModule(Module):
    _gui_config = ModuleGuiConfig("MyModule", Categories.FILTERS, "Does something useful.")

    def __init__(self, module_id=None):
        super().__init__(module_id)
    [end:subclass]
[start:ports]
self.inputs = InputPorts(
    InputPort("images", dict),
)
self.outputs = OutputPorts(
    OutputPort("result", dict),
)
[end:ports]
[start:settings]
self.user_threshold: float = 0.5
self.limit_user_threshold = Limit(min_val=0.0, max_val=1.0)
[end:settings]

[start:run]
def run(self) -> bool:
    data = self.inputs.images.data   # read input
    # ... process data
    self.outputs.result.data = data  # write output
    return False
[end:run]