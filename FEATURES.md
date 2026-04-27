# Features

This project is a browser-based causal graph workbench with a small local Python import service. The goal is to make graphs from different causal tools feel like they belong in one clean viewer, where they can be explored, edited, saved, and exported.

## Importing Graphs

The viewer can import graphs from Tetrad, causal-learn, DoWhy, Dagitty, and the project's canonical JSON format. The browser sends the chosen file to the local Python service, which translates each source format into one shared graph structure before the graph is drawn.

## Local Launcher

`launcher.py` starts the import server and opens the viewer in the default browser. It also has a `--no-browser` option for running only the server when the viewer is opened manually.

## Shared Graph Schema

The Python model gives every graph the same shape: graph metadata, nodes, edges, endpoint types, layout data, visual styling, and extra attributes. This keeps the viewer from needing separate drawing logic for every upstream tool.

## Endpoint-Aware Edge Drawing

Edges are drawn with causal endpoint types instead of plain arrows only. The app supports tails, arrows, circles, bidirected edges, undirected edges, and partially oriented edges, which makes it useful for DAGs, CPDAGs, PAGs, MAGs, and similar causal graph outputs.

## Canvas Navigation

The graph canvas supports zooming with the mouse wheel, panning by dragging empty space, and moving individual nodes by dragging them. This makes it easy to clean up a dense graph without leaving the viewer.

## Automatic Layout

Imported graphs get arranged automatically when they do not already include layout coordinates. The app can use a hierarchical layout when the graph direction is clear, and it falls back to a circular layout when that is more appropriate.

## View Fitting

After import, the viewer can fit the graph into the visible canvas so the user starts with a useful view instead of having to hunt around for the graph.

## Target Selection

The sidebar has a multi-select target list. Selected nodes are highlighted with a configurable target color, making it easier to keep important variables visible while exploring.

## Scope Filtering

The target scope control can show the full graph or narrow the view around selected nodes. It supports neighbors, parents, children, ancestors, and descendants.

## Edge Threshold Filtering

The visibility threshold hides weaker edges based on available strength information. The app uses confidence values when present, falls back to absolute edge weights when available, and otherwise treats edges as fully visible.

## Edge Styling By Metric

Edges can change transparency or thickness based on confidence, beta/weight, or an automatic strength setting. This gives a quick visual sense of which relationships are stronger without changing the graph itself.

## Edge Labels

Edge labels can show weight/beta values, confidence values, automatic labels, or no labels. The label size can also be adjusted from the sidebar.

## Node Styling

Right-clicking a node opens a small style editor for changing color, transparency, size, and shape. Supported shapes include circles, squares, and diamonds.

## Edge Styling

Right-clicking an edge opens style controls for color, transparency, width, and bend. Edge bend is useful when multiple edges connect the same pair of nodes or when a straight line would make the graph harder to read.

## Manual Layout Nudging

The layout section includes Edge Pull and Vertex Push buttons. Holding these buttons gently adjusts the layout, helping connected nodes move closer together or crowded nodes spread apart.

## Legend Import

The viewer can load matching legend JSON from the local server for supported sample graphs. Legends appear as draggable panels over the canvas and can also be included in exported images.

## Viewer Guide

The info button opens an in-app guide that explains the main workflow: importing, target scopes, edge filters, editing, legends, sessions, exporting, and canvas controls.

## Persistent Preferences

The app saves several interface choices in browser local storage, including sidebar width, threshold, edge label mode, edge label size, target color, target scope, export type, and edge filter modes.

## Session Save And Load

Sessions can be saved as JSON and loaded later. A session preserves the baseline graph, the current edited graph, selected targets, filter settings, camera position, sidebar width, export type, and legend state.

## Layout Snapshot Export

The current graph state can be exported as a layout JSON file. This is useful when the graph has been manually arranged and the layout should be reused or inspected outside the viewer.

## Final Image Export

The canvas can be exported as PNG, JPEG, WebP, or SVG. The export uses an offscreen render so the final image reflects the current graph view and visible legend.

## Reset View

Reset View restores the original imported graph state, clears temporary edits, resets the camera, rebuilds the target list, and hides the legend.

## Sample Inputs

The `sample v3 inputs` folder provides example graph files and legend data for testing the import flow. These are useful demo fixtures for checking that the same graph can travel through different source formats.

## Graph Utilities

The Python helper functions can find parents, children, ancestors, descendants, Markov blankets, and induced subgraphs. These utilities support graph analysis work outside the browser and mirror some of the relationship logic used by the viewer.
