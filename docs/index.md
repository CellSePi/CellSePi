<div class="hero-tag">Docs</div>
# Building a module

Modules are the core building blocks of a CellSePi pipeline. Each module is responsible for a single, well-defined task, such as reading files, segmenting images, or exporting results. It connects seamlessly to other modules through ports.

<a href="guide/quickstart/" class="next-card" style="margin-bottom: 2rem; display: block;">
  <span class="next-card-label">Get started</span>
  <span class="next-card-title">Quick start →</span>
  <span class="next-card-sub">Build your first module step by step.</span>
</a>

Below you find more detailed instructions for the individual concepts:

<div class="custom-card-grid">
  <a href="guide/subclass/" class="custom-card">
    <h4><span class="card-num">1</span> Subclass <code>Module</code></h4>
    <p>Inherit from the base class to seamlessly integrate into the pipeline.</p>
  </a>
  <a href="guide/ports/" class="custom-card">
    <h4><span class="card-num">2</span> Declare ports</h4>
    <p>Define the input and output ports that connect this module to others in the pipeline.</p>
  </a>
  <a href="guide/settings/" class="custom-card">
    <h4><span class="card-num">3</span> Define settings</h4>
    <p>Configure automatic GUI generation using <code>user_</code> attributes, or provide custom layouts for full control.</p>
  </a>
  <a href="guide/run/" class="custom-card">
    <h4><span class="card-num">4</span> Implement <code>run()</code></h4>
    <p>Define the core processing logic where your module executes its primary task.</p>
  </a>
  <a href="guide/plugin/" class="custom-card">
    <h4><span class="card-num">5</span> Launch the plugin</h4>
    <p>Place your Python module in the <code>plugins</code> directory to make it available in CellSePi.</p>
  </a>
</div>

<h2 id="module-example">What a module looks like</h2>


```python
--8<-- "docs/examples/my_module.py"
```


<a href="guide/examples/" class="next-card" style="margin-top: 1rem;">
  <span class="next-card-label">Going deeper</span>
  <span class="next-card-title">Examples →</span>
  <span class="next-card-sub">Explore practical examples within the CellSePi ecosystem.</span>
</a>
