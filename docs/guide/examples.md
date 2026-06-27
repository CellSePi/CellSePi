<a href="/" class="back-card">
  <span class="back-card-icon">←</span>
  <span>
    <span class="back-card-label">Back to</span>
    <span class="back-card-title">Home</span>
  </span>
</a>

<div class="hero-tag">Examples</div>
<h1>Module Examples</h1>

<p>Explore practical examples that demonstrate how to use custom GUIs and reactive settings within the CellSePi ecosystem.</p>

## 1. Image Segmentation Module
This module demonstrates how to apply <b>Limit</b> for parameter validation and how to build reactive settings using the auto-generated GUI controls.
```python
--8<-- "cellsepi/backend/expert_mode/modules/image_segmentation.py"
```

## 2. Review Module
This module showcases how to implement a custom GUI for manual user interaction during a pipeline pause.

```python
--8<-- "cellsepi/backend/expert_mode/modules/review.py"
```