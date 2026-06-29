<section id="quickstart">
  <a href="../../" class="back-card">
  <span class="back-card-icon">←</span>
  <span>
    <span class="back-card-label">Back to</span>
    <span class="back-card-title">Home</span>
  </span>
</a>
  <div class="hero-tag">Workflow</div>
  <h1>Quick start</h1>
  <p>Building a module is simple: write your code, drop it into the <code>plugins/</code> folder, and you are ready to go.</p>
  <div class="step">
    <div class="step-num">1</div>
    <div class="step-body" markdown="1">
      <h4>Subclass <code>Module</code></h4>
      <p>Inherit from the base class and define your GUI config. <a href="../subclass/" class="step-detail-link">Learn more</a></p>

```python
{%include-markdown "examples/my_module_steps.py" start="[start:subclass]" end="[end:subclass]"%}
```

    </div>
  </div>
  <div class="step">
    <div class="step-num">2</div>
    <div class="step-body" markdown="1">
      <h4>Declare ports</h4>
      <p>Define your input and output ports in the constructor. <a href="../ports/" class="step-detail-link">Learn more</a></p>

```python
{%include-markdown "examples/my_module_steps.py" start="[start:ports]" end="[end:ports]"%}
```

    </div>
  </div>
  <div class="step">
    <div class="step-num">3</div>
    <div class="step-body" markdown="1">
      <h4>Define settings</h4>
      <p>Add <code>user_</code> attributes to automatically generate your GUI controls. <a href="../settings/" class="step-detail-link">Learn more</a></p>

```python
{%include-markdown "examples/my_module_steps.py" start="[start:settings]" end="[end:settings]"%}
```

    </div>
  </div>
  <div class="step">
    <div class="step-num">4</div>
    <div class="step-body" markdown="1">
      <h4>Implement <code>run()</code></h4>
      <p>Write your core logic to process the data. <a href="../run/" class="step-detail-link">Learn more</a></p>

```python
{%include-markdown "examples/my_module_steps.py" start="[start:run]" end="[end:run]"%}
```

    </div>
  </div>
  <div class="step">
    <div class="step-num">5</div>
    <div class="step-body">
      <h4>Launch the plugin</h4>
      <p>Save your file in the the <code>plugins/</code> folder and restart CellSePi. Your module will appear automatically in the expert mode. <a href="../plugin/" class="step-detail-link">Learn more</a></p>
    </div>
  </div>
</section>