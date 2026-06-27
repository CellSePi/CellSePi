<a href="../../" class="back-card">
  <span class="back-card-icon">←</span>
  <span>
    <span class="back-card-label">Back to</span>
    <span class="back-card-title">Home</span>
  </span>
</a>

<div class="hero-tag">Guide · Step 2</div>
<h1>Declare ports</h1>

<p>Define the input and output ports that connect this module to others in the pipeline. Declare them in <code>__init__</code> by assigning to <code>self.inputs</code> and <code>self.outputs</code>.</p>

## Basic example
!!! warning "Important Rule for Port Naming"
    Ports with the same name in different modules **must always have the same `data_type`**. 
    Because identical port names are treated as the same conceptual connection, mixing different data types (e.g., setting `"images"` as `dict` in Module A, but as `list` in Module B) is not allowed.
    If a `Pipe` attempts to transfer data between mismatched ports, it will immediately raise a `TypeError` during execution (`"Type mismatch on port..."`).

```python
def __init__(self, module_id=None):
    super().__init__(module_id)
    self.inputs = InputPorts(
        InputPort("images", dict),           # mandatory
        InputPort("masks",  dict, opt=True), # optional
    )
    self.outputs = OutputPorts(
        OutputPort("result", dict),
    )
```

## Accessing port data in `run()`

Access port data via attribute name on `self.inputs` and `self.outputs`:

```python
{% include-markdown "../examples/MyModule.py" start="[start:run]" end="[end:run]" preserve_includer_indent=false %}
```

---

## Input Ports

::: backend.expert_mode.ports.InputPort
    options:
      show_root_heading: false
      show_source: false
      show_if_no_docstring: true
      members: []

### InputPort multi modes

!!! warning
    Tagged multi-ports show a tag-selection dialog when the user connects a pipe. Always provide the allowed tags as a set of strings.

The `multi` parameter controls how many incoming connections an input port accepts, and how the data is structured.

<div class="custom-card-grid">
  <div class="custom-card static-card">
    <h4><code>multi = False</code> — default</h4>
    <p>One incoming pipe, one value. Suitable for most standard cases.</p>
  </div>
  
  <div class="custom-card static-card">
    <h4><code>multi = True</code></h4>
    <p>Accepts multiple incoming pipes. Data arrives as a list of values, useful for merging streams.</p>
  </div>
  
  <div class="custom-card static-card">
    <h4><code>multi = {"tag1", "tag2"}</code></h4>
    <p>Multiple pipes, managed by a specific set of tags. Data arrives as a dictionary keyed by these user-chosen tags.</p>
  </div>
</div>

### Mandatory vs optional

By default, all input ports are **mandatory**. If a module's mandatory ports are unconnected, the pipeline will show a warning before executing. It will inform you that the affected modules will be skipped and give you the option to either cancel and fix the connections, or proceed with the run anyway.

Mark a port as optional with `opt=True`:

```python
InputPort("mask_paths", dict, opt=True)
```

---

## Output Ports

::: backend.expert_mode.ports.OutputPort
    options:
      show_root_heading: false
      show_source: false
      show_if_no_docstring: true
      members: []

<div class="custom-card-grid" style="margin-top: 2rem;">
  <a href="../settings/" class="next-card">
    <span class="next-card-label">Next</span>
    <span class="next-card-title">Define settings →</span>
    <span class="next-card-sub">Add user-configurable settings with automatic GUI generation.</span>
  </a>
  <a href="../quickstart/" class="next-card">
    <span class="next-card-label">Or go here</span>
    <span class="next-card-title">Quick start →</span>
    <span class="next-card-sub">Build a complete module step by step.</span>
  </a>
</div>