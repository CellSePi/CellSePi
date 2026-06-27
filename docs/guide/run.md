<a href="../../" class="back-card">
  <span class="back-card-icon">←</span>
  <span>
    <span class="back-card-label">Back to</span>
    <span class="back-card-title">Home</span>
  </span>
</a>

<div class="hero-tag">Guide · Step 4</div>
<h1>Implement run()</h1>

<p>The <code>run()</code> method is the core engine of your module. The pipeline executes this method automatically when all preceding modules have successfully finished. This is where you read incoming data, apply your processing logic, and push the results to your output ports.</p>

## Basic structure

```python
def run(self) -> bool:
    # 1. Read inputs
    images = self.inputs.images.data

    # 2. Do work
    result = process(images)

    # 3. Write outputs
    self.outputs.result.data = result

    # 4. Return False to continue, True to pause
    return False
```

## Return value

<div class="custom-card-grid">
  <div class="custom-card static-card">
    <h4>Return <code>False</code></h4>
    <p>Pipeline continues to the next module immediately.</p>
  </div>
  <div class="custom-card static-card">
    <h4>Return <code>True</code></h4>
    <p>Pipeline pauses after this module. While paused, the module's <strong>settings become available again</strong>, allowing the user to adjust parameters. The user must press <strong>Resume</strong> to continue. Useful for review or manual steps.</p>
  </div>
</div>

## Cancellation

Check `self.is_cancelled()` periodically inside long loops. When it returns `True`, stop processing and return early:

```python
def run(self) -> bool:
    for i, item in enumerate(self.inputs.items.data):
        if self.is_cancelled():
            return False
        process(item)
    return False
```
## Error handling

!!! info "Automatic error catching"
    You don't need to wrap your entire `run()` method in `try...except` blocks. The CellSePi pipeline automatically catches **all unhandled exceptions** (like `KeyError`, `IndexError`, or unexpected third-party library crashes), stops the pipeline safely, and reports the error to the GUI.

If your module encounters a critical issue (e.g., bad data formats, missing files), you should stop execution safely. Import and raise a `PipelineRunningException` to instantly halt the pipeline and display a formatted error dialog in the UI.

```python
from backend.expert_mode.pipeline_manager import PipelineRunningException

def run(self) -> bool:
    image = self.inputs.images.data
    
    # Validate data shape
    if image.ndim != 3:
        raise PipelineRunningException("Value Error", "Wrong image format, expected a 3D image.")
    
    return False
```

## Reporting progress

Use the <code>EventManager</code> to send progress updates with a percentage (0-100) and a status message to the GUI:

```python
def run(self) -> bool:
    items = self.inputs.items.data
    total = len(items)

    self.event_manager.notify(ProgressEvent(percent=0, process="Starting processing..."))

    for i, item in enumerate(items):
        if self.is_cancelled():
            self.event_manager.notify(ProgressEvent(percent=int(i / total * 100), process="Cancelled!"))
            return False

        process(item)

        self.event_manager.notify(
            ProgressEvent(percent=int((i + 1) / total * 100), process=f"Processing item {i + 1}/{total}")
        )

    self.event_manager.notify(ProgressEvent(percent=100, process="Finished"))
    return False
```

## Post-processing & Cleanup (`finished`)

The pipeline calls the `finished()` method after `run()` completes (and directly after the pipeline is resumed, if `run()` returned `True` to pause). 

While this is the standard place to safely clean up temporary resources or free memory, it is also the perfect place to **apply final logic based on user interactions** that happened during a pause.

```python
def finished(self):
    # 1. Process data based on new user input if the pipeline was paused
    if self.user_apply_extra_filter:
        self.outputs.result.data = apply_filter(self.outputs.result.data)

    # 2. Clean up temporary resources
    self._temp_buffer = None
```

<div class="custom-card-grid" style="margin-top: 2rem;">
  <a href="../plugin/" class="next-card">
    <span class="next-card-label">Next</span>
    <span class="next-card-title">Launch the plugin →</span>
    <span class="next-card-sub">Place your Python module in the <code>plugins</code> directory to make it available in CellSePi.</span>
  </a>
  <a href="../quickstart/" class="next-card">
    <span class="next-card-label">Or go here</span>
    <span class="next-card-title">Quick start →</span>
    <span class="next-card-sub">Build a complete module step by step.</span>
  </a>
</div>