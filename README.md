# Causal Graph Visualizer

Causal Graph Visualizer is a small research-oriented tool for viewing, comparing, and preparing causal graphs from several common causal-analysis packages. The goal is to make it easier to inspect graph structure, preserve important endpoint semantics, and export clear figures for presentations, posters, papers, and exploratory analysis.

The viewer runs in the browser and uses a lightweight local import service to translate supported graph formats into a shared internal representation.

**Download For Windows**

[Download `CausalGraphVisualizer.exe`](https://github.com/aarav2703/Causal-Graph-Visualizer/raw/main/CausalGraphVisualizer.exe)

On some Windows systems, SmartScreen may show a warning for newly built academic or open-source executables. If you prefer not to use the `.exe`, the project can also be run directly from source with Python.

Supported imports:

- Tetrad
- causal-learn
- DoWhy
- Dagitty
- Canonical JSON

Current features:

- Import graphs from several causal-analysis tools
- Preserve directed, undirected, bidirected, and circle-endpoint edge types
- Zoom, pan, and drag nodes for manual layout refinement
- Filter around selected target nodes
- Show neighbors, parents, children, ancestors, or descendants
- Edit node and edge appearance in the viewer
- Save sessions and export layout JSON
- Export final figures as `PNG`, `JPEG`, `WebP`, or `SVG`

The current viewer entry point is [Causal viewer_v3/index.html](./Causal%20viewer_v3/index.html).

**Running From Source**

If you are not using the Windows executable, open PowerShell in the repo root and run:

```powershell
$env:PYTHONPATH='.'
python .\launcher.py
```

This starts the local import server and opens the viewer in your default browser.

You can also start only the import service:

```powershell
$env:PYTHONPATH='.'
python .\scripts\import_graph_server.py
```

Then open [Causal viewer_v3/index.html](./Causal%20viewer_v3/index.html) in your browser.

**Sample Files**

The folder [sample v3 inputs](./sample%20v3%20inputs) contains small example graphs that are useful for trying the viewer quickly. These files are intended to show how different source formats are normalized into the same visual workspace.

- `causal_learn_complex_pag.txt` is a good first example because it includes a richer mixed-edge PAG-style graph.
- `tetrad_complex_pag.txt` demonstrates Tetrad-style edge notation and partially oriented edges.
- `dagitty_sample.txt` gives a compact Dagitty-style graph.
- `dowhy_sample.dot` provides a simple DoWhy/DOT-style input.

Additional generated parser fixtures are available in [parser_test_outputs](./parser_test_outputs). Those files are more technical and are mainly useful for checking parser compatibility across Tetrad, causal-learn, Dagitty, and DoWhy raw outputs.

Basic import flow:

1. Start the app, either with the Windows `.exe` or with `python .\launcher.py`.
2. In the viewer, pick a source format.
3. Choose a matching graph file.
4. Click `Import Graph`.
5. Optionally load or edit a legend.
6. Explore, edit, and export the graph.

**Screenshots**
Main workspace with the sidebar controls, loaded complex sample graph, and legend panel:

![Main viewer workspace](./docs/screenshots/viewer-workspace.png)

Edge styling editor opened on a graph edge:

![Edge style editor](./docs/screenshots/edge-style-editor.png)

**Development Notes**
- The viewer starts empty until a graph is imported.
- Import and legend loading depend on the local Python server.
- Browser settings such as threshold, label mode, target color, and sidebar width are saved locally.
- Session save/load and layout export are available from the viewer UI.
