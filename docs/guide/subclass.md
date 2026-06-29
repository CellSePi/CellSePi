<a href="../../" class="back-card">
  <span class="back-card-icon">←</span>
  <span>
    <span class="back-card-label">Back to</span>
    <span class="back-card-title">Home</span>
  </span>
</a>

<div class="hero-tag">Guide · Step 1</div>
<h1>Subclass Module</h1>

<p>Every CellSePi module inherits from the abstract <code>Module</code> base class. By defining a <code>_gui_config</code>, your module gets its identity in the pipeline: a unique name, a category and a description.</p>

## The base class

Import everything you need from the module package:

```python
from backend.expert_mode.module import *
```

This imports `Module`, `ModuleGuiConfig`, `Categories`, `InputPorts`, `OutputPorts`, `InputPort`, `OutputPort`, `Limit`, `FilePath`, `DirectoryPath`, `EventManager`, and `ProgressEvent`. This is everything required to build a module. More on the last two in Step <a href="../run/" class="Step-4">4</a>.

## Defining the class

!!! info
    Always call `super().__init__(module_id)` as the first line of `__init__`. This registers the module with the pipeline and assigns it a unique ID.

```python
class MyModule(Module):
    _gui_config = ModuleGuiConfig(
        "MyModule",
        Categories.FILTERS,
        "Does something useful."
    )
    
    def __init__(self, module_id=None):
        super().__init__(module_id)
```

## `_gui_config` explained

::: backend.expert_mode.module.ModuleGuiConfig
    options:
      show_root_heading: false
      show_source: false
      show_root_toc_entry: false
      members: []

## Categories

!!! warning
    Red and green are reserved for pipeline status indicators.

| Category | Color                                                                                                                           | Use for |
|----------|------------------------------------------------------------------------------------------------------------------------------|---------|
| `Categories.INPUTS` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#FF9800;vertical-align:middle"></span> | Reading files, loading data |
| `Categories.OUTPUTS` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#03A9F4;vertical-align:middle"></span> | Exporting results, saving files |
| `Categories.FILTERS` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#E040FB;vertical-align:middle"></span> | Transforming or filtering data |
| `Categories.MANUAL` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#E91E63;vertical-align:middle"></span> | Modules requiring user interaction |
| `Categories.SEGMENTATION` | <span style="display:inline-block;width:14px;height:14px;border-radius:3px;background:#FFD740;vertical-align:middle"></span> | Different kinds of segmentation |

## Naming rules

!!! warning
    The `name` in `_gui_config` must be **globally unique** across all built-in modules and plugins. If a plugin's name already exists, it will be skipped on startup and an error is logged.

Use clear, descriptive names:

| Good | Bad |
|------|-----|
| `ImageSegmentation` | `module1` |
| `SpotDetection` | `Segmentation` |
| `ReadFiles` | `read` |

<div class="custom-card-grid" style="margin-top: 2rem;">
  <a href="../ports/" class="next-card">
    <span class="next-card-label">Next</span>
    <span class="next-card-title">Declare ports →</span>
    <span class="next-card-sub">Define the available input and output ports that users can connect to the pipeline.</span>
  </a>
  <a href="../quickstart/" class="next-card">
    <span class="next-card-label">Or go here</span>
    <span class="next-card-title">Quick start →</span>
    <span class="next-card-sub">Build a complete module step by step.</span>
  </a>
</div>