<a href="../../" class="back-card">
  <span class="back-card-icon">←</span>
  <span>
    <span class="back-card-label">Back to</span>
    <span class="back-card-title">Home</span>
  </span>
</a>

<div class="hero-tag">Guide · Step 5</div>
<h1>Launch the plugin</h1>

## The `plugins` directory

!!! info
    CellSePi automatically scans the `plugins` directory on startup, finds all classes inheriting from the `Module` base class, and registers them automatically.

CellSePi uses a drop-in plugin system. Your modules are stored in a hidden folder in your user directory: 
`~/.cellsepi/plugins/`.

You don't need to navigate there manually. You can simply open the directory from within the application:

1. Open **Options** in the top-right corner of the application.
   
    ![Options button](../assets/options.png)

2. Click the **Plugins** button directly in the menu. This opens the folder for you.
    
    ![Plugins folder button](../assets/plugins.png)

3. Drop your Python file into this folder.

    ![Plugins folder](../assets/folder.png)

---

## Restart CellSePi

Save your file and restart the application. Your module will automatically appear in the show room on the left side of the expert mode.

## Checklist

<div class="custom-card-grid">
  <div class="custom-card static-card">
    <h4>✓ Unique name</h4>
    <p>The <code>_gui_config</code> name is unique across all modules.</p>
  </div>
  <div class="custom-card static-card">
    <h4>✓ super().__init__</h4>
    <p>Called as the first line of <code>__init__</code>.</p>
  </div>
  <div class="custom-card static-card">
    <h4>✓ Ports declared</h4>
    <p>All <code>InputPorts</code> and <code>OutputPorts</code> defined in <code>__init__</code>.</p>
  </div>
  <div class="custom-card static-card">
    <h4>✓ run() implementation</h4>
    <p>Logic implemented. Returning <code>True</code> pauses the pipeline for review.</p>
  </div>
  <div class="custom-card static-card">
    <h4>✓ Outputs assigned</h4>
    <p>Data assigned to output ports ensures pipeline integrity.</p>
  </div>
  <div class="custom-card static-card">
    <h4>✓ Placed in plugins</h4>
    <p>The Python file is located in the <code>plugins</code> directory.</p>
  </div>
</div>

<div class="custom-card-grid" style="margin-top: 2rem;">
  <a href="../examples/" class="next-card">
    <span class="next-card-label">Next</span>
    <span class="next-card-title">Examples →</span>
    <span class="next-card-sub">
Explore practical examples within the CellSePi ecosystem.</span>
  </a>
  <a href="../quickstart/" class="next-card">
    <span class="next-card-label">Or go here</span>
    <span class="next-card-title">Quick start →</span>
    <span class="next-card-sub">Build your first module step by step.</span>
  </a>
</div>