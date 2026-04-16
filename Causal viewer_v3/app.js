(() => {
  // Global viewer defaults, local-server endpoints, and sample legend mappings.
  const BACKGROUND = "#e9edf4";
  const LABEL_FONT = { style: "16px Segoe UI", color: "#293042" };
  const RADIUS = 28;
  const MIN_SCALE = 0.35;
  const MAX_SCALE = 3.5;
  const GLOBAL_PREFERENCES_KEY = "causal-viewer-v3-global-preferences";
  const SERVER_URL = "http://127.0.0.1:8765/api/import";
  const LEGEND_URL = "http://127.0.0.1:8765/api/legend";
  const DEFAULT_GLOBAL_PREFERENCES = {
    viewer: {
      sidebar_width: 28,
      threshold: 0,
      edge_alpha_filter_mode: "off",
      edge_width_filter_mode: "off",
      edge_label_mode: "auto",
      edge_label_size: 12,
      target_color: "#4f7cff",
      target_scope: "all",
      export_type: "png",
      auto_fit_on_import: true,
      layout_on_import: "hierarchical"
    },
    style: {
      default_node_size: 28,
      default_edge_width: 4,
      node_type_colors: {
        observed: "rgba(200, 200, 200, 0.58)",
        latent: "rgba(115, 118, 132, 0.75)",
        exposure: "rgba(53, 127, 188, 0.78)",
        outcome: "rgba(198, 92, 58, 0.78)",
        selection: "rgba(164, 108, 42, 0.78)",
        adjusted: "rgba(99, 145, 91, 0.74)",
        unknown: "rgba(176, 181, 193, 0.62)"
      },
      edge_colors: {
        positive: "rgba(204, 66, 66, 0.75)",
        negative: "rgba(70, 98, 206, 0.75)",
        neutral: "rgba(41, 48, 66, 0.55)"
      }
    }
  };
  const LEGEND_BY_FILENAME = {
    "tetrad_sample.txt": "simple",
    "causal_learn_sample.txt": "simple",
    "dagitty_sample.txt": "simple",
    "dowhy_sample.dot": "simple",
    "tetrad_complex_pag.txt": "tetrad_complex_pag",
    "causal_learn_complex_pag.txt": "complex_pag",
    "dagitty_complex_pag.txt": "complex_pag",
    "dowhy_complex_pag.json": "complex_pag"
  };

  const dom = {
    container: document.getElementById("container"),
    sidebar: document.getElementById("sidebar"),
    divider: document.getElementById("divider"),
    canvasContainer: document.getElementById("canvas-container"),
    canvas: document.getElementById("canvas"),
    targetSelect: document.getElementById("target-select"),
    targetColor: document.getElementById("target-color"),
    targetScope: document.getElementById("target-scope"),
    thresholdSlider: document.getElementById("threshold-slider"),
    thresholdLabel: document.getElementById("threshold-label"),
    edgeAlphaFilterMode: document.getElementById("edge-alpha-filter-mode"),
    edgeWidthFilterMode: document.getElementById("edge-width-filter-mode"),
    edgeLabelMode: document.getElementById("edge-label-mode"),
    edgeLabelSize: document.getElementById("edge-label-size"),
    edgeLabelSizeLabel: document.getElementById("edge-label-size-label"),
    widthSlider: document.getElementById("width-slider"),
    widthLabel: document.getElementById("width-label"),
    edgeStep: document.getElementById("edge-step"),
    vertexStep: document.getElementById("vertex-step"),
    exportType: document.getElementById("export-type"),
    saveSessionBtn: document.getElementById("save-session-btn"),
    loadSessionBtn: document.getElementById("load-session-btn"),
    exportImageBtn: document.getElementById("export-image-btn"),
    exportLayoutBtn: document.getElementById("export-layout-btn"),
    resetViewBtn: document.getElementById("reset-view-btn"),
    viewerGuideBtn: document.getElementById("viewer-guide-btn"),
    parserSelect: document.getElementById("parser-select"),
    fileInput: document.getElementById("graph-file-input"),
    sessionFileInput: document.getElementById("session-file-input"),
    importBtn: document.getElementById("import-btn"),
    importLegendBtn: document.getElementById("import-legend-btn"),
    importStatus: document.getElementById("import-status"),
    status: document.getElementById("status"),
    styleEditor: document.getElementById("style-editor"),
    styleEditorTitle: document.getElementById("style-editor-title"),
    styleEditorClose: document.getElementById("style-editor-close"),
    nodeStyleFields: document.getElementById("node-style-fields"),
    edgeStyleFields: document.getElementById("edge-style-fields"),
    nodeColorInput: document.getElementById("style-node-color"),
    nodeAlphaInput: document.getElementById("style-node-alpha"),
    nodeSizeInput: document.getElementById("style-node-size"),
    nodeShapeInput: document.getElementById("style-node-shape"),
    edgeColorInput: document.getElementById("style-edge-color"),
    edgeAlphaInput: document.getElementById("style-edge-alpha"),
    edgeWidthInput: document.getElementById("style-edge-width"),
    edgeBendInput: document.getElementById("style-edge-bend"),
    edgeBendLabel: document.getElementById("style-edge-bend-label"),
    legendPanel: document.getElementById("legend-panel"),
    legendHeader: document.getElementById("legend-header"),
    legendTitle: document.getElementById("legend-title"),
    legendSubtitle: document.getElementById("legend-subtitle"),
    legendBody: document.getElementById("legend-body"),
    viewerGuideModal: document.getElementById("viewer-guide-modal"),
    viewerGuideCard: document.getElementById("viewer-guide-card"),
    viewerGuideClose: document.getElementById("viewer-guide-close")
  };

  const ctx = dom.canvas.getContext("2d");

  // Runtime state for camera position, graph data, editing tools, legend placement, and preferences.
  const state = {
    scale: 1,
    offsetX: 0,
    offsetY: 0,
    selectedIndex: -1,
    selectedDX: 0,
    selectedDY: 0,
    resizeActive: false,
    dragCanvas: false,
    dragStartX: 0,
    dragStartY: 0,
    pullActive: false,
    pushActive: false,
    styleTarget: null,
    legendDragActive: false,
    legendDragOffsetX: 0,
    legendDragOffsetY: 0,
    graphName: "",
    graphType: "",
    originalGraph: null,
    originalFilename: null,
    currentFilename: null,
    preferences: cloneData(DEFAULT_GLOBAL_PREFERENCES),
    nodes: [],
    edges: [],
    idToIndex: new Map()
  };

  function setStatus(message) {
    dom.status.textContent = message;
  }

  function setImportStatus(message) {
    dom.importStatus.textContent = message;
  }

  function hexToRgba(hex, alpha = 1) {
    const normalized = hex.replace("#", "");
    const r = parseInt(normalized.slice(0, 2), 16);
    const g = parseInt(normalized.slice(2, 4), 16);
    const b = parseInt(normalized.slice(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  function rgbaToHex(color) {
    const match = color.match(/\d+/g);
    if (!match || match.length < 3) return "#c8c8c8";
    const [r, g, b] = match.slice(0, 3).map((value) => Number(value).toString(16).padStart(2, "0"));
    return `#${r}${g}${b}`;
  }

  function rgbaAlpha(color) {
    const match = color.match(/rgba\(\s*\d+\s*,\s*\d+\s*,\s*\d+\s*,\s*([0-9.]+)\s*\)/);
    return match ? Number(match[1]) : 1;
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function screenToWorld(offsetX, offsetY) {
    return {
      x: (offsetX - state.offsetX) / state.scale,
      y: (offsetY - state.offsetY) / state.scale
    };
  }

  function eventToCanvasOffset(event) {
    const rect = dom.canvas.getBoundingClientRect();
    return {
      x: event.clientX - rect.left,
      y: event.clientY - rect.top
    };
  }

  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(reader.error || new Error("Failed to read file"));
      reader.readAsText(file);
    });
  }

  function cloneData(data) {
    return JSON.parse(JSON.stringify(data));
  }

  function mergeDeep(base, override) {
    if (!override || typeof override !== "object" || Array.isArray(override)) {
      return cloneData(base);
    }
    const result = cloneData(base);
    Object.entries(override).forEach(([key, value]) => {
      if (
        value &&
        typeof value === "object" &&
        !Array.isArray(value) &&
        result[key] &&
        typeof result[key] === "object" &&
        !Array.isArray(result[key])
      ) {
        result[key] = mergeDeep(result[key], value);
      } else {
        result[key] = value;
      }
    });
    return result;
  }

  function loadGlobalPreferences() {
    // Restore persisted viewer defaults from local storage.
    try {
      const raw = window.localStorage.getItem(GLOBAL_PREFERENCES_KEY);
      if (!raw) return cloneData(DEFAULT_GLOBAL_PREFERENCES);
      return mergeDeep(DEFAULT_GLOBAL_PREFERENCES, JSON.parse(raw));
    } catch (_) {
      return cloneData(DEFAULT_GLOBAL_PREFERENCES);
    }
  }

  function saveGlobalPreferences() {
    try {
      window.localStorage.setItem(GLOBAL_PREFERENCES_KEY, JSON.stringify(state.preferences));
    } catch (_) {
      // Ignore storage persistence failures.
    }
  }

  function syncPreferencesFromControls() {
    // Persist the current control-panel values as the active viewer baseline.
    state.preferences.viewer = mergeDeep(state.preferences.viewer, {
      sidebar_width: Number(dom.widthSlider.value),
      threshold: Number(dom.thresholdSlider.value),
      edge_alpha_filter_mode: dom.edgeAlphaFilterMode.value,
      edge_width_filter_mode: dom.edgeWidthFilterMode.value,
      edge_label_mode: dom.edgeLabelMode.value,
      edge_label_size: Number(dom.edgeLabelSize.value),
      target_color: dom.targetColor.value,
      target_scope: dom.targetScope.value,
      export_type: dom.exportType.value
    });
    saveGlobalPreferences();
  }

  function applyGlobalPreferencesToControls() {
    const prefs = state.preferences.viewer;
    dom.targetColor.value = prefs.target_color;
    dom.targetScope.value = prefs.target_scope;
    dom.thresholdSlider.value = String(prefs.threshold);
    dom.thresholdLabel.textContent = `${dom.thresholdSlider.value}%`;
    dom.edgeAlphaFilterMode.value = prefs.edge_alpha_filter_mode;
    dom.edgeWidthFilterMode.value = prefs.edge_width_filter_mode;
    dom.edgeLabelMode.value = prefs.edge_label_mode;
    dom.edgeLabelSize.value = String(prefs.edge_label_size);
    dom.edgeLabelSizeLabel.textContent = `${dom.edgeLabelSize.value}px`;
    dom.exportType.value = prefs.export_type;
    setSidebarWidth(prefs.sidebar_width);
  }

  function deepCloneNodes() {
    return state.nodes.map((node) => ({
      x: node.layout.x,
      y: node.layout.y,
      hidden: node.hidden
    }));
  }

  function getSelectedTargets() {
    const selected = [];
    for (const option of dom.targetSelect.options) {
      if (option.selected) selected.push(Number(option.value));
    }
    return selected;
  }

  function isDirectedForward(edge) {
    return edge.endpoints.source === "tail" && edge.endpoints.target === "arrow";
  }

  function isDirectedBackward(edge) {
    return edge.endpoints.source === "arrow" && edge.endpoints.target === "tail";
  }

  function collectImmediate(scope, selected) {
    // Compute one-hop neighborhoods for neighbor, parent, and child filtering modes.
    const visible = new Set(selected);

    state.edges.forEach((edge) => {
      const sourceIndex = state.idToIndex.get(edge.source);
      const targetIndex = state.idToIndex.get(edge.target);
      if (sourceIndex === undefined || targetIndex === undefined) return;

      if (scope === "neighbors") {
        if (selected.has(sourceIndex) || selected.has(targetIndex)) {
          visible.add(sourceIndex);
          visible.add(targetIndex);
        }
        return;
      }

      if (scope === "parents") {
        if (isDirectedForward(edge) && selected.has(targetIndex)) visible.add(sourceIndex);
        if (isDirectedBackward(edge) && selected.has(sourceIndex)) visible.add(targetIndex);
        return;
      }

      if (scope === "children") {
        if (isDirectedForward(edge) && selected.has(sourceIndex)) visible.add(targetIndex);
        if (isDirectedBackward(edge) && selected.has(targetIndex)) visible.add(sourceIndex);
      }
    });

    return visible;
  }

  function collectReachable(direction, selected) {
    // Traverse directed structure to build ancestor or descendant visibility sets.
    const visible = new Set(selected);
    const queue = [...selected];

    while (queue.length > 0) {
      const current = queue.shift();
      state.edges.forEach((edge) => {
        const sourceIndex = state.idToIndex.get(edge.source);
        const targetIndex = state.idToIndex.get(edge.target);
        if (sourceIndex === undefined || targetIndex === undefined) return;

        let next = null;
        if (direction === "ancestors") {
          if (isDirectedForward(edge) && targetIndex === current) next = sourceIndex;
          if (isDirectedBackward(edge) && sourceIndex === current) next = targetIndex;
        } else {
          if (isDirectedForward(edge) && sourceIndex === current) next = targetIndex;
          if (isDirectedBackward(edge) && targetIndex === current) next = sourceIndex;
        }

        if (next !== null && !visible.has(next)) {
          visible.add(next);
          queue.push(next);
        }
      });
    }

    return visible;
  }

  function computeScopeNodes(selected) {
    const scope = dom.targetScope.value;
    if (scope === "all" || selected.size === 0) return null;
    if (scope === "neighbors" || scope === "parents" || scope === "children") {
      return collectImmediate(scope, selected);
    }
    if (scope === "ancestors" || scope === "descendants") {
      return collectReachable(scope, selected);
    }
    return null;
  }

  function inferEdgeStrength(edge) {
    // Normalize available edge metrics into a single strength value for filtering and styling.
    if (typeof edge.attributes.confidence === "number") {
      return edge.attributes.confidence;
    }
    if (typeof edge.weight === "number") {
      return clamp(Math.abs(edge.weight), 0, 1);
    }
    return 1;
  }

  function inferEdgeColor(edge) {
    if (edge.viz?.color) return edge.viz.color;
    if (typeof edge.weight === "number") {
      return edge.weight < 0
        ? state.preferences.style.edge_colors.negative
        : state.preferences.style.edge_colors.positive;
    }
    return state.preferences.style.edge_colors.neutral;
  }

  function applyAlphaMultiplier(color, multiplier) {
    const alpha = clamp(rgbaAlpha(color) * multiplier, 0.08, 1);
    return hexToRgba(rgbaToHex(color), alpha);
  }

  function inferEdgeTransparencyMetric(edge) {
    const mode = dom.edgeAlphaFilterMode.value;
    if (mode === "off") return 1;
    return inferEdgeMetricForMode(edge, mode);
  }

  function inferEdgeMetricForMode(edge, mode) {
    if (mode === "off") return 1;
    if (mode === "confidence") {
      return typeof edge.attributes.confidence === "number"
        ? clamp(edge.attributes.confidence, 0, 1)
        : 1;
    }
    if (mode === "beta") {
      return typeof edge.weight === "number" ? clamp(Math.abs(edge.weight), 0, 1) : 1;
    }
    return inferEdgeStrength(edge);
  }

  function inferEdgeRenderColor(edge) {
    const baseColor = edge.displayColor;
    if (dom.edgeAlphaFilterMode.value === "off") return baseColor;
    const metric = inferEdgeTransparencyMetric(edge);
    const multiplier = 0.18 + 0.82 * metric;
    return applyAlphaMultiplier(baseColor, multiplier);
  }

  function inferEdgeRenderWidth(edge) {
    const baseWidth = edge.width || 4;
    const mode = dom.edgeWidthFilterMode.value;
    if (mode === "off") return baseWidth;
    const metric = inferEdgeMetricForMode(edge, mode);
    const widthScale = 0.45 + 1.55 * metric;
    return clamp(baseWidth * widthScale, 1.5, 16);
  }

  function inferNodeColor(node) {
    if (node.viz?.color) return node.viz.color;
    return (
      state.preferences.style.node_type_colors[node.node_type] ||
      state.preferences.style.node_type_colors.unknown
    );
  }

  function inferNodeSize(node) {
    return typeof node.viz?.size === "number"
      ? node.viz.size
      : state.preferences.style.default_node_size;
  }

  function inferNodeShape(node) {
    return node.viz?.shape || "circle";
  }

  function inferEdgeWidth(edge) {
    return typeof edge.viz?.width === "number"
      ? edge.viz.width
      : state.preferences.style.default_edge_width;
  }

  function inferLegacyCurveBend(edge) {
    const mode = edge.viz?.curveMode;
    if (!mode || mode === "straight") return 0;
    const strength =
      typeof edge.viz?.curveStrength === "number"
        ? clamp(edge.viz.curveStrength, 0, 1)
        : 0.45;
    const direction = edge.viz?.curveDirection || "auto";
    if (direction === "left") return strength;
    if (direction === "right") return -strength;
    const pairOffset = getPairIndex(edge);
    return pairOffset < 0 ? -strength : strength;
  }

  function inferEdgeBend(edge) {
    if (typeof edge.viz?.curveBend === "number") {
      return clamp(edge.viz.curveBend, -1, 1);
    }
    return inferLegacyCurveBend(edge);
  }

  function endpointPair(edge) {
    return `${edge.endpoints.source}:${edge.endpoints.target}`;
  }

  function getEdgeLabelSize() {
    return Number(dom.edgeLabelSize.value);
  }

  function describeEdgeBend(bendValue) {
    if (Math.abs(bendValue) <= 0.02) return "Straight";
    const magnitude = Math.round(Math.abs(bendValue) * 100);
    return bendValue < 0 ? `${magnitude}% right` : `${magnitude}% left`;
  }

  function getVisibleGraphCenter(context) {
    const visibleNodes = state.nodes.filter((node) => !node.hidden);
    if (visibleNodes.length === 0) {
      return { x: context.canvas.width / 2, y: context.canvas.height / 2 };
    }
    let sumX = 0;
    let sumY = 0;
    visibleNodes.forEach((node) => {
      const center = nodeCenterFor(context, node);
      sumX += center.x;
      sumY += center.y;
    });
    return {
      x: sumX / visibleNodes.length,
      y: sumY / visibleNodes.length
    };
  }

  function getPairIndex(edge) {
    const pairKey = [edge.source, edge.target].sort().join("::");
    const related = state.edges.filter(
      (item) => [item.source, item.target].sort().join("::") === pairKey
    );
    const position = related.findIndex((item) => item === edge);
    return position - (related.length - 1) / 2;
  }

  function computeEdgeGeometry(context, edge) {
    // Resolve node-relative layouts into concrete edge endpoints on the canvas.
    const source = state.nodes[state.idToIndex.get(edge.source)];
    const target = state.nodes[state.idToIndex.get(edge.target)];
    const p1 = nodeCenterFor(context, source);
    const p2 = nodeCenterFor(context, target);
    const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
    const sourceRadius = source.size || RADIUS;
    const targetRadius = target.size || RADIUS;
    const start = {
      x: p1.x + sourceRadius * Math.cos(angle),
      y: p1.y + sourceRadius * Math.sin(angle)
    };
    const end = {
      x: p2.x - targetRadius * Math.cos(angle),
      y: p2.y - targetRadius * Math.sin(angle)
    };

    const bend = inferEdgeBend(edge);
    const curved = Math.abs(bend) > 0.02;
    if (!curved) {
      return { curved: false, start, end, sourceRadius, targetRadius };
    }

    const midpoint = { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 };
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const length = Math.max(Math.hypot(dx, dy), 1);
    const nx = -dy / length;
    const ny = dx / length;
    const signedOffset = 92 * bend;
    let control = {
      x: midpoint.x + nx * signedOffset,
      y: midpoint.y + ny * signedOffset
    };

    return {
      curved: true,
      start,
      end,
      control,
      sourceRadius,
      targetRadius
    };
  }

  function getEdgeLabelText(edge) {
    const mode = dom.edgeLabelMode.value;
    if (mode === "none") return null;
    if (mode === "weight") {
      return typeof edge.weight === "number" ? `${edge.weight.toFixed(2)}` : null;
    }
    if (mode === "confidence") {
      return typeof edge.attributes.confidence === "number"
        ? `${edge.attributes.confidence.toFixed(2)}`
        : null;
    }
    if (mode === "auto") {
      if (typeof edge.weight === "number") return `${edge.weight.toFixed(2)}`;
      if (typeof edge.attributes.confidence === "number") {
        return `${edge.attributes.confidence.toFixed(2)}`;
      }
    }
    return null;
  }

  function hasVisibleEdgeLabels() {
    if (dom.edgeLabelMode.value === "none") return false;
    return state.edges.some((edge) => !edge.hidden && getEdgeLabelText(edge));
  }

  function getQuadraticPoint(start, control, end, t) {
    const oneMinusT = 1 - t;
    return {
      x: oneMinusT * oneMinusT * start.x + 2 * oneMinusT * t * control.x + t * t * end.x,
      y: oneMinusT * oneMinusT * start.y + 2 * oneMinusT * t * control.y + t * t * end.y
    };
  }

  function getQuadraticTangent(start, control, end, t) {
    return {
      x: 2 * (1 - t) * (control.x - start.x) + 2 * t * (end.x - control.x),
      y: 2 * (1 - t) * (control.y - start.y) + 2 * t * (end.y - control.y)
    };
  }

  function drawEdgeLabel(context, edge, geometry) {
    // Draw inline weight/confidence labels using the active edge label mode.
    const text = getEdgeLabelText(edge);
    if (!text) return;

    let labelPoint;
    if (geometry.curved) {
      labelPoint = getQuadraticPoint(geometry.start, geometry.control, geometry.end, 0.5);
    } else {
      labelPoint = {
        x: (geometry.start.x + geometry.end.x) / 2,
        y: (geometry.start.y + geometry.end.y) / 2
      };
    }

    context.save();
    const fontSize = getEdgeLabelSize();
    context.font = `${fontSize}px Segoe UI`;
    context.textAlign = "center";
    context.textBaseline = "middle";
    const metrics = context.measureText(text);
    const width = metrics.width + Math.max(12, fontSize * 0.8);
    const height = Math.max(20, fontSize + 8);
    context.fillStyle = "rgba(255,255,255,0.92)";
    context.strokeStyle = "rgba(76, 86, 106, 0.25)";
    context.lineWidth = 1;
    context.beginPath();
    context.roundRect(labelPoint.x - width / 2, labelPoint.y - height / 2, width, height, 8);
    context.fill();
    context.stroke();
    context.fillStyle = "#1f2430";
    context.fillText(text, labelPoint.x, labelPoint.y + 0.5);
    context.restore();
  }

  function graphHasExplicitLayout(data) {
    return (data.nodes || []).every(
      (node) =>
        typeof node.layout?.x === "number" &&
        typeof node.layout?.y === "number"
    );
  }

  function getDirectedAdjacency(data) {
    const adjacency = new Map();
    const indegree = new Map();
    (data.nodes || []).forEach((node) => {
      adjacency.set(node.id, []);
      indegree.set(node.id, 0);
    });

    (data.edges || []).forEach((edge) => {
      let sourceId = null;
      let targetId = null;
      if (edge.endpoints?.source === "tail" && edge.endpoints?.target === "arrow") {
        sourceId = edge.source;
        targetId = edge.target;
      } else if (edge.endpoints?.source === "arrow" && edge.endpoints?.target === "tail") {
        sourceId = edge.target;
        targetId = edge.source;
      }
      if (!sourceId || !targetId) return;
      adjacency.get(sourceId)?.push(targetId);
      indegree.set(targetId, (indegree.get(targetId) || 0) + 1);
    });

    return { adjacency, indegree };
  }

  function applyCircleLayout(data) {
    // Fallback layout for graphs that arrive without coordinates.
    const nodes = data.nodes || [];
    const count = Math.max(nodes.length, 1);
    nodes.forEach((node, index) => {
      const angle = (-Math.PI / 2) + (index / count) * Math.PI * 2;
      node.layout = {
        x: 0.5 + 0.34 * Math.cos(angle),
        y: 0.5 + 0.30 * Math.sin(angle)
      };
    });
  }

  function applyHierarchicalLayout(data) {
    // DAG-oriented import layout that uses edge direction to assign layers.
    const nodes = data.nodes || [];
    if (nodes.length === 0) return;

    const { adjacency, indegree } = getDirectedAdjacency(data);
    const queue = [];
    const layers = new Map();

    nodes.forEach((node) => {
      if ((indegree.get(node.id) || 0) === 0) queue.push(node.id);
      layers.set(node.id, 0);
    });

    const visited = new Set();
    while (queue.length > 0) {
      const current = queue.shift();
      visited.add(current);
      const currentLayer = layers.get(current) || 0;
      (adjacency.get(current) || []).forEach((next) => {
        layers.set(next, Math.max(layers.get(next) || 0, currentLayer + 1));
        indegree.set(next, (indegree.get(next) || 0) - 1);
        if ((indegree.get(next) || 0) <= 0) queue.push(next);
      });
    }

    if (visited.size === 0 || [...layers.values()].every((layer) => layer === 0)) {
      applyCircleLayout(data);
      return;
    }

    nodes.forEach((node, index) => {
      if (!visited.has(node.id)) {
        layers.set(node.id, (index % 3) + 1);
      }
    });

    const maxLayer = Math.max(...layers.values(), 0);
    const grouped = new Map();
    nodes.forEach((node) => {
      const layer = layers.get(node.id) || 0;
      if (!grouped.has(layer)) grouped.set(layer, []);
      grouped.get(layer).push(node);
    });

    [...grouped.values()].forEach((group) => {
      group.sort((a, b) => a.id.localeCompare(b.id));
    });

    grouped.forEach((group, layer) => {
      const x = maxLayer === 0 ? 0.5 : 0.12 + (0.76 * layer) / maxLayer;
      group.forEach((node, index) => {
        const y =
          group.length === 1
            ? 0.5
            : 0.14 + (0.72 * index) / Math.max(group.length - 1, 1);
        node.layout = {
          x: Number(x.toFixed(4)),
          y: Number(y.toFixed(4))
        };
      });
    });
  }

  function arrangeImportedGraph(data) {
    // Apply an import-time layout only when the source graph has no explicit node positions.
    if (graphHasExplicitLayout(data)) return;
    const mode = state.preferences.viewer.layout_on_import;
    if (mode === "circle") {
      applyCircleLayout(data);
      return;
    }
    applyHierarchicalLayout(data);
  }

  function fitViewToGraph() {
    // Recenter and zoom so the currently visible graph fits in the viewport.
    const visibleNodes = state.nodes.filter((node) => !node.hidden);
    if (visibleNodes.length === 0) {
      state.scale = 1;
      state.offsetX = 0;
      state.offsetY = 0;
      return;
    }

    const xs = visibleNodes.map((node) => node.layout.x * ctx.canvas.width);
    const ys = visibleNodes.map((node) => node.layout.y * ctx.canvas.height);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const padding = 80;
    const graphWidth = Math.max(maxX - minX, 120);
    const graphHeight = Math.max(maxY - minY, 120);
    const scaleX = (ctx.canvas.width - padding * 2) / graphWidth;
    const scaleY = (ctx.canvas.height - padding * 2) / graphHeight;
    state.scale = clamp(Math.min(scaleX, scaleY, 1.35), MIN_SCALE, MAX_SCALE);
    const centerX = (minX + maxX) / 2;
    const centerY = (minY + maxY) / 2;
    state.offsetX = ctx.canvas.width / 2 - centerX * state.scale;
    state.offsetY = ctx.canvas.height / 2 - centerY * state.scale;
  }

  function normalizeGraph(data) {
    // Convert canonical graph JSON into the richer in-memory viewer model.
    arrangeImportedGraph(data);
    state.graphName = data.graph?.name || "Imported Graph";
    state.graphType = data.graph?.graph_type || "DAG";
    state.nodes = data.nodes.map((node, index) => ({
      id: node.id,
      label: node.label || node.id,
      observed: node.observed !== false,
      node_type: node.node_type || (node.observed === false ? "latent" : "observed"),
      group: node.group || null,
      attributes: node.attributes || {},
      viz: node.viz || {},
      layout: {
        x: typeof node.layout?.x === "number" ? node.layout.x : 0.12 + ((index % 5) * 0.16),
        y: typeof node.layout?.y === "number" ? node.layout.y : 0.14 + (Math.floor(index / 5) * 0.16)
      },
      hidden: false,
      displayColor: inferNodeColor(node),
      size: inferNodeSize(node),
      shape: inferNodeShape(node)
    }));

    state.idToIndex = new Map(state.nodes.map((node, index) => [node.id, index]));

    state.edges = data.edges.map((edge) => ({
      source: edge.source,
      target: edge.target,
      endpoints: {
        source: edge.endpoints.source,
        target: edge.endpoints.target
      },
      lag: edge.lag ?? 0,
      weight: edge.weight,
      attributes: edge.attributes || {},
      viz: edge.viz || {},
      hidden: false,
      strength: inferEdgeStrength(edge),
      displayColor: inferEdgeColor(edge),
      width: inferEdgeWidth(edge)
    }));

    if (state.preferences.viewer.edge_label_mode === "auto") {
      if (state.edges.some((edge) =>
        typeof edge.weight === "number" || typeof edge.attributes.confidence === "number"
      )) {
        dom.edgeLabelMode.value = "auto";
      } else {
        dom.edgeLabelMode.value = "none";
      }
    }
  }

  function clearGraph() {
    // Reset the viewer to an empty state and remove graph-specific UI overlays.
    state.graphName = "";
    state.graphType = "";
    state.originalGraph = null;
    state.originalFilename = null;
    state.currentFilename = null;
    state.nodes = [];
    state.edges = [];
    state.idToIndex = new Map();
    state.selectedIndex = -1;
    dom.targetSelect.innerHTML = "";
    hideStyleEditor();
    hideLegend();
    draw();
  }

  function rebuildTargetOptions() {
    dom.targetSelect.innerHTML = "";
    state.nodes.forEach((node, index) => {
      const option = document.createElement("option");
      option.value = String(index);
      option.textContent = node.label.replaceAll("_", " ");
      dom.targetSelect.appendChild(option);
    });
  }

  function resizeCanvas() {
    dom.canvas.width = dom.canvasContainer.clientWidth;
    dom.canvas.height = dom.canvasContainer.clientHeight;
    draw();
  }

  function setSidebarWidth(percent) {
    const clamped = clamp(percent, 18, 48);
    dom.sidebar.style.width = `${clamped}%`;
    dom.widthSlider.value = String(Math.round(clamped));
    dom.widthLabel.textContent = `${Math.round(clamped)}%`;
    resizeCanvas();
  }

  function updateFilters() {
    // Recompute node and edge visibility from threshold and target-scope settings.
    const threshold = Number(dom.thresholdSlider.value) / 100;
    const selected = new Set(getSelectedTargets());
    const scopedNodes = computeScopeNodes(selected);
    const color = dom.targetColor.value;
    const targetRgba = `${color}EE`;

    state.edges.forEach((edge) => {
      const sourceIndex = state.idToIndex.get(edge.source);
      const targetIndex = state.idToIndex.get(edge.target);
      const outOfScope =
        scopedNodes !== null &&
        (!scopedNodes.has(sourceIndex) || !scopedNodes.has(targetIndex));
      edge.hidden = edge.strength < threshold || outOfScope;
    });

    state.nodes.forEach((node, index) => {
      node.hidden = scopedNodes !== null && !scopedNodes.has(index);
      node.displayColor = node.viz?.color || inferNodeColor(node);
      if (selected.has(index)) {
        node.displayColor = targetRgba;
      }
    });

    draw();
  }

  function nodeCenter(node) {
    return {
      x: ctx.canvas.width * node.layout.x,
      y: ctx.canvas.height * node.layout.y
    };
  }

  function nodeCenterFor(context, node) {
    return {
      x: context.canvas.width * node.layout.x,
      y: context.canvas.height * node.layout.y
    };
  }

  function drawNode(context, node) {
    // Render the node body, latent styling, and multiline label text.
    const center = nodeCenterFor(context, node);
    const lines = node.label.split("_");
    const size = node.size || RADIUS;

    // Paint a solid backdrop first so translucent node fills do not reveal edges underneath.
    context.fillStyle = BACKGROUND;
    context.beginPath();
    if (node.shape === "square") {
      context.rect(center.x - size - 3, center.y - size - 3, (size + 3) * 2, (size + 3) * 2);
    } else if (node.shape === "diamond") {
      context.moveTo(center.x, center.y - size - 3);
      context.lineTo(center.x + size + 3, center.y);
      context.lineTo(center.x, center.y + size + 3);
      context.lineTo(center.x - size - 3, center.y);
      context.closePath();
    } else {
      context.arc(center.x, center.y, size + 3, 0, Math.PI * 2);
    }
    context.fill();

    context.fillStyle = node.displayColor;
    context.beginPath();
    if (node.shape === "square") {
      context.rect(center.x - size, center.y - size, size * 2, size * 2);
    } else if (node.shape === "diamond") {
      context.moveTo(center.x, center.y - size);
      context.lineTo(center.x + size, center.y);
      context.lineTo(center.x, center.y + size);
      context.lineTo(center.x - size, center.y);
      context.closePath();
    } else {
      context.arc(center.x, center.y, size, 0, Math.PI * 2);
    }
    context.fill();

    if (node.node_type === "latent") {
      context.strokeStyle = "rgba(54, 60, 70, 0.85)";
      context.setLineDash([5, 4]);
      context.lineWidth = 2;
      context.stroke();
      context.setLineDash([]);
    }

    context.fillStyle = LABEL_FONT.color;
    context.font = LABEL_FONT.style;
    context.textAlign = "center";
    context.textBaseline = "middle";

    let shift = ((1 - lines.length) * 16) / 2;
    lines.forEach((line) => {
      context.fillText(line, center.x, center.y + shift);
      shift += 16;
    });
  }

  function drawArrowhead(context, x, y, length, angle) {
    context.beginPath();
    context.moveTo(x, y);
    context.lineTo(
      x - length * Math.cos(angle) + (length / 2) * Math.sin(angle),
      y - length * Math.sin(angle) - (length / 2) * Math.cos(angle)
    );
    context.lineTo(x - length * Math.cos(angle), y - length * Math.sin(angle));
    context.lineTo(
      x - length * Math.cos(angle) - (length / 2) * Math.sin(angle),
      y - length * Math.sin(angle) + (length / 2) * Math.cos(angle)
    );
    context.closePath();
    context.fill();
  }

  function drawCircleEndpoint(context, x, y, radius) {
    context.beginPath();
    context.arc(x, y, radius, 0, Math.PI * 2);
    context.stroke();
  }

  function maskLineUnderArrowhead(context, x, y, angle, length, lineWidth) {
    // Hide the stroke segment beneath each arrowhead so the marker reads as one shape.
    context.save();
    context.strokeStyle = BACKGROUND;
    context.lineWidth = Math.max(lineWidth + 4, length * 0.7);
    context.beginPath();
    context.moveTo(x - length * Math.cos(angle), y - length * Math.sin(angle));
    context.lineTo(x, y);
    context.stroke();
    context.restore();
  }

  function drawEdge(context, edge) {
    // Render the edge path, endpoint markers, and any enabled edge label.
    const source = state.nodes[state.idToIndex.get(edge.source)];
    const target = state.nodes[state.idToIndex.get(edge.target)];
    if (!source || !target) return;
    if (source.hidden || target.hidden || edge.hidden) return;

    const geometry = computeEdgeGeometry(context, edge);
    const targetMarker = geometry.targetRadius * 0.72;
    const sourceMarker = geometry.sourceRadius * 0.72;

    const renderColor = inferEdgeRenderColor(edge);
    const renderWidth = inferEdgeRenderWidth(edge);
    context.strokeStyle = renderColor;
    context.fillStyle = renderColor;
    context.lineWidth = renderWidth;
    context.beginPath();
    context.moveTo(geometry.start.x, geometry.start.y);
    if (geometry.curved) {
      context.quadraticCurveTo(
        geometry.control.x,
        geometry.control.y,
        geometry.end.x,
        geometry.end.y
      );
    } else {
      context.lineTo(geometry.end.x, geometry.end.y);
    }
    context.stroke();

    let targetAngle;
    let sourceAngle;
    if (geometry.curved) {
      const targetTangent = getQuadraticTangent(
        geometry.start,
        geometry.control,
        geometry.end,
        1
      );
      const sourceTangent = getQuadraticTangent(
        geometry.start,
        geometry.control,
        geometry.end,
        0
      );
      targetAngle = Math.atan2(targetTangent.y, targetTangent.x);
      sourceAngle = Math.atan2(sourceTangent.y, sourceTangent.x);
    } else {
      targetAngle = Math.atan2(
        geometry.end.y - geometry.start.y,
        geometry.end.x - geometry.start.x
      );
      sourceAngle = targetAngle;
    }

    if (edge.endpoints.target === "arrow") {
      maskLineUnderArrowhead(
        context,
        geometry.end.x,
        geometry.end.y,
        targetAngle,
        targetMarker,
        renderWidth
      );
      context.fillStyle = renderColor;
      drawArrowhead(context, geometry.end.x, geometry.end.y, targetMarker, targetAngle);
    } else if (edge.endpoints.target === "circle") {
      drawCircleEndpoint(
        context,
        geometry.end.x + 6 * Math.cos(targetAngle),
        geometry.end.y + 6 * Math.sin(targetAngle),
        6
      );
    }

    if (edge.endpoints.source === "arrow") {
      maskLineUnderArrowhead(
        context,
        geometry.start.x,
        geometry.start.y,
        sourceAngle + Math.PI,
        sourceMarker,
        renderWidth
      );
      context.fillStyle = renderColor;
      drawArrowhead(context, geometry.start.x, geometry.start.y, sourceMarker, sourceAngle + Math.PI);
    } else if (edge.endpoints.source === "circle") {
      drawCircleEndpoint(
        context,
        geometry.start.x - 6 * Math.cos(sourceAngle),
        geometry.start.y - 6 * Math.sin(sourceAngle),
        6
      );
    }

    drawEdgeLabel(context, edge, geometry);
  }

  function drawLegendToCanvas(context) {
    // Repaint the floating legend panel into export output.
    if (dom.legendPanel.classList.contains("hidden")) return;

    const left = parseFloat(dom.legendPanel.style.left || "28");
    const top = parseFloat(dom.legendPanel.style.top || "28");
    const width = Math.min(320, context.canvas.width - left - 16);
    let y = top;

    context.save();
    context.fillStyle = "rgba(255, 255, 255, 0.97)";
    context.strokeStyle = "rgba(76, 86, 106, 0.2)";
    context.lineWidth = 1;
    const lineHeight = 18;
    const title = dom.legendTitle.textContent || "Legend";
    const subtitle = dom.legendSubtitle.textContent || "";
    const sections = [...dom.legendBody.querySelectorAll(".legend-section")];
    const estimatedHeight = 60 + sections.reduce((sum, section) => {
      return sum + 26 + section.querySelectorAll(".legend-item").length * 42;
    }, 0);
    context.beginPath();
    context.roundRect(left, top, width, estimatedHeight, 14);
    context.fill();
    context.stroke();

    context.fillStyle = "#1f2430";
    context.font = "bold 16px Segoe UI";
    context.textAlign = "left";
    context.textBaseline = "top";
    context.fillText(title, left + 12, y + 12);
    y += 32;

    if (subtitle) {
      context.fillStyle = "#5c6578";
      context.font = "12px Segoe UI";
      context.fillText(subtitle, left + 12, y);
      y += 28;
    }

    sections.forEach((section) => {
      const heading = section.querySelector("h3")?.textContent || "";
      context.fillStyle = "#485165";
      context.font = "bold 12px Segoe UI";
      context.fillText(heading, left + 12, y);
      y += 20;

      [...section.querySelectorAll(".legend-item")].forEach((item) => {
        const symbol = item.querySelector(".legend-symbol")?.textContent || "";
        const label = item.querySelector(".legend-copy strong")?.textContent || "";
        const description = item.querySelector(".legend-copy p")?.textContent || "";

        context.fillStyle = "rgba(232, 236, 244, 0.9)";
        context.strokeStyle = "rgba(76, 86, 106, 0.14)";
        context.beginPath();
        context.roundRect(left + 12, y, 72, 28, 10);
        context.fill();
        context.stroke();

        context.fillStyle = "#334";
        context.font = "12px Segoe UI";
        context.fillText(symbol, left + 20, y + 7);

        context.fillStyle = "#1f2430";
        context.font = "bold 13px Segoe UI";
        context.fillText(label, left + 96, y + 2);

        context.fillStyle = "#5c6578";
        context.font = "12px Segoe UI";
        context.fillText(description, left + 96, y + 18);
        y += 42;
      });
      y += 6;
    });
    context.restore();
  }

  function renderScene(context) {
    // Single-pass renderer for the graph canvas.
    context.fillStyle = BACKGROUND;
    context.fillRect(0, 0, context.canvas.width, context.canvas.height);

    if (state.nodes.length === 0) {
      context.fillStyle = "rgba(56, 64, 80, 0.7)";
      context.font = "18px Segoe UI";
      context.textAlign = "center";
      context.textBaseline = "middle";
      context.fillText("Import a graph to begin", context.canvas.width / 2, context.canvas.height / 2);
      return;
    }

    context.save();
    context.translate(state.offsetX, state.offsetY);
    context.scale(state.scale, state.scale);

    state.edges.forEach((edge) => drawEdge(context, edge));
    state.nodes.forEach((node) => {
      if (!node.hidden) drawNode(context, node);
    });

    context.restore();
  }

  function draw() {
    renderScene(ctx);
  }

  function findNodeIndexAt(offsetX, offsetY) {
    // Hit test visible nodes in reverse draw order for dragging and context actions.
    const pointer = screenToWorld(offsetX, offsetY);
    for (let index = state.nodes.length - 1; index >= 0; index -= 1) {
      const node = state.nodes[index];
      if (node.hidden) continue;
      const center = nodeCenter(node);
      const dx = center.x - pointer.x;
      const dy = center.y - pointer.y;
      const size = node.size || RADIUS;
      if (dx * dx + dy * dy <= size * size) return index;
    }
    return -1;
  }

  function distanceToSegment(px, py, x1, y1, x2, y2) {
    const vx = x2 - x1;
    const vy = y2 - y1;
    const wx = px - x1;
    const wy = py - y1;
    const c1 = vx * wx + vy * wy;
    if (c1 <= 0) return Math.hypot(px - x1, py - y1);
    const c2 = vx * vx + vy * vy;
    if (c2 <= c1) return Math.hypot(px - x2, py - y2);
    const b = c1 / c2;
    const bx = x1 + b * vx;
    const by = y1 + b * vy;
    return Math.hypot(px - bx, py - by);
  }

  function findEdgeIndexAt(offsetX, offsetY) {
    // Approximate hit testing for straight and curved edges.
    const pointer = screenToWorld(offsetX, offsetY);
    let bestIndex = -1;
    let bestDistance = Infinity;
    for (let index = 0; index < state.edges.length; index += 1) {
      const edge = state.edges[index];
      const source = state.nodes[state.idToIndex.get(edge.source)];
      const target = state.nodes[state.idToIndex.get(edge.target)];
      if (!source || !target || source.hidden || target.hidden || edge.hidden) continue;
      const geometry = computeEdgeGeometry(ctx, edge);
      let distance;
      if (geometry.curved) {
        let bestCurveDistance = Infinity;
        let previous = geometry.start;
        for (let step = 1; step <= 24; step += 1) {
          const current = getQuadraticPoint(
            geometry.start,
            geometry.control,
            geometry.end,
            step / 24
          );
          bestCurveDistance = Math.min(
            bestCurveDistance,
            distanceToSegment(pointer.x, pointer.y, previous.x, previous.y, current.x, current.y)
          );
          previous = current;
        }
        distance = bestCurveDistance;
      } else {
        distance = distanceToSegment(
          pointer.x,
          pointer.y,
          geometry.start.x,
          geometry.start.y,
          geometry.end.x,
          geometry.end.y
        );
      }
      if (distance < bestDistance) {
        bestDistance = distance;
        bestIndex = index;
      }
    }
    return bestDistance <= 8 ? bestIndex : -1;
  }

  function hideStyleEditor() {
    state.styleTarget = null;
    dom.styleEditor.classList.add("hidden");
  }

  function hideLegend() {
    state.legendDragActive = false;
    dom.legendPanel.classList.add("hidden");
  }

  function showViewerGuide() {
    dom.viewerGuideModal.classList.remove("hidden");
  }

  function hideViewerGuide() {
    dom.viewerGuideModal.classList.add("hidden");
  }

  function inferLegendKey() {
    // Infer the best legend definition from the active sample filename or graph type.
    if (state.currentFilename && LEGEND_BY_FILENAME[state.currentFilename]) {
      return LEGEND_BY_FILENAME[state.currentFilename];
    }
    if (state.graphType === "PAG" || state.graphType === "MAG" || state.graphType === "CPDAG") {
      return "complex_pag";
    }
    if (state.graphType === "DAG" || state.graphType === "PDAG") {
      return "simple";
    }
    return null;
  }

  function renderLegendSymbol(symbol) {
    const symbols = {
      "node-circle": "Node",
      "target-highlight": "Target",
      "tail-arrow": "A -> B",
      "tail-tail": "A -- B",
      "arrow-arrow": "A <-> B",
      "circle-arrow": "A o-> B",
      "circle-circle": "A o-o B",
      tip: "Tip"
    };
    return symbols[symbol] || symbol;
  }

  function renderLegend(legend, clientX, clientY) {
    // Materialize legend JSON into the draggable floating legend panel.
    dom.legendTitle.textContent = legend.title || "Legend";
    dom.legendSubtitle.textContent = legend.subtitle || "";
    dom.legendBody.innerHTML = "";

    (legend.sections || []).forEach((section) => {
      const sectionEl = document.createElement("section");
      sectionEl.className = "legend-section";
      const heading = document.createElement("h3");
      heading.textContent = section.heading || "";
      sectionEl.appendChild(heading);

      (section.items || []).forEach((item) => {
        const itemEl = document.createElement("div");
        itemEl.className = "legend-item";

        const symbol = document.createElement("div");
        symbol.className = "legend-symbol";
        symbol.textContent = renderLegendSymbol(item.symbol);

        const copy = document.createElement("div");
        copy.className = "legend-copy";
        const label = document.createElement("strong");
        label.textContent = item.label || "";
        const description = document.createElement("p");
        description.textContent = item.description || "";
        copy.appendChild(label);
        copy.appendChild(description);

        itemEl.appendChild(symbol);
        itemEl.appendChild(copy);
        sectionEl.appendChild(itemEl);
      });

      dom.legendBody.appendChild(sectionEl);
    });

    const rect = dom.canvasContainer.getBoundingClientRect();
    const desiredLeft = Math.max(12, clientX - rect.left);
    const desiredTop = Math.max(12, clientY - rect.top);
    dom.legendPanel.style.left = `${desiredLeft}px`;
    dom.legendPanel.style.top = `${desiredTop}px`;
    dom.legendPanel.classList.remove("hidden");

    // After layout, clamp the panel fully inside the canvas area without adding a scrollbar.
    const legendRect = dom.legendPanel.getBoundingClientRect();
    const maxLeft = Math.max(12, rect.width - legendRect.width - 12);
    const maxTop = Math.max(12, rect.height - legendRect.height - 12);
    dom.legendPanel.style.left = `${Math.min(desiredLeft, maxLeft)}px`;
    dom.legendPanel.style.top = `${Math.min(desiredTop, maxTop)}px`;
  }

  async function loadLegendAtPosition(clientX, clientY) {
    // Fetch the mapped legend payload from the local server and place it near the pointer.
    const legendKey = inferLegendKey();
    if (!legendKey) {
      setStatus("No sample legend is mapped for the current graph.");
      return;
    }

    let response;
    try {
      response = await fetch(`${LEGEND_URL}?key=${encodeURIComponent(legendKey)}`);
    } catch (_) {
      setStatus("Legend server request failed. Start python scripts/import_graph_server.py");
      return;
    }

    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      setStatus(payload.error || "Failed to load legend.");
      return;
    }

    renderLegend(payload.legend, clientX, clientY);
    setStatus(`Loaded ${payload.key} legend.`);
  }

  async function loadLegendFromButton() {
    if (state.nodes.length === 0) {
      setStatus("Import a graph before loading a legend.");
      return;
    }

    const rect = dom.canvasContainer.getBoundingClientRect();
    await loadLegendAtPosition(rect.left + 28, rect.top + 28);
  }

  async function handleCanvasContextMenu(event) {
    event.preventDefault();
    event.stopPropagation();

    const canvasRect = dom.canvas.getBoundingClientRect();
    const offsetX = event.clientX - canvasRect.left;
    const offsetY = event.clientY - canvasRect.top;

    const nodeIndex = findNodeIndexAt(offsetX, offsetY);
    if (nodeIndex !== -1) {
      hideLegend();
      showStyleEditor("node", nodeIndex, event.clientX, event.clientY);
      return;
    }

    const edgeIndex = findEdgeIndexAt(offsetX, offsetY);
    if (edgeIndex !== -1) {
      hideLegend();
      showStyleEditor("edge", edgeIndex, event.clientX, event.clientY);
      return;
    }

    hideStyleEditor();
    await loadLegendAtPosition(event.clientX, event.clientY);
  }

  function showStyleEditor(type, index, clientX, clientY) {
    // Open the style editor for a specific node or edge target.
    state.styleTarget = { type, index };
    dom.styleEditorTitle.textContent = type === "node" ? "Edit Node Style" : "Edit Edge Style";
    dom.nodeStyleFields.style.display = type === "node" ? "grid" : "none";
    dom.edgeStyleFields.style.display = type === "edge" ? "grid" : "none";
    dom.styleEditor.classList.remove("hidden");
    const rect = dom.canvasContainer.getBoundingClientRect();
    dom.styleEditor.style.left = `${Math.max(12, clientX - rect.left)}px`;
    dom.styleEditor.style.top = `${Math.max(12, clientY - rect.top)}px`;

    if (type === "node") {
      const node = state.nodes[index];
      dom.nodeColorInput.value = rgbaToHex(node.viz?.color || inferNodeColor(node));
      dom.nodeAlphaInput.value = String(rgbaAlpha(node.viz?.color || inferNodeColor(node)));
      dom.nodeSizeInput.value = String(node.size || RADIUS);
      dom.nodeShapeInput.value = node.shape || "circle";
    } else {
      const edge = state.edges[index];
      dom.edgeColorInput.value = rgbaToHex(edge.viz?.color || edge.displayColor);
      dom.edgeAlphaInput.value = String(rgbaAlpha(edge.viz?.color || edge.displayColor));
      dom.edgeWidthInput.value = String(edge.width || 4);
      const bend = inferEdgeBend(edge);
      dom.edgeBendInput.value = String(Math.round(bend * 100));
      dom.edgeBendLabel.textContent = describeEdgeBend(bend);
    }
  }

  function applyStyleEditor() {
    // Write style edits directly back into the active runtime graph.
    if (!state.styleTarget) return;
    if (state.styleTarget.type === "node") {
      const node = state.nodes[state.styleTarget.index];
      node.viz = node.viz || {};
      node.viz.color = hexToRgba(dom.nodeColorInput.value, Number(dom.nodeAlphaInput.value));
      node.viz.size = Number(dom.nodeSizeInput.value);
      node.viz.shape = dom.nodeShapeInput.value;
      node.displayColor = node.viz.color;
      node.size = node.viz.size;
      node.shape = node.viz.shape;
    } else {
      const edge = state.edges[state.styleTarget.index];
      edge.viz = edge.viz || {};
      edge.viz.color = hexToRgba(dom.edgeColorInput.value, Number(dom.edgeAlphaInput.value));
      edge.viz.width = Number(dom.edgeWidthInput.value);
      edge.viz.curveBend = Number(dom.edgeBendInput.value) / 100;
      delete edge.viz.curveMode;
      delete edge.viz.curveDirection;
      delete edge.viz.curveStrength;
      edge.displayColor = edge.viz.color;
      edge.width = edge.viz.width;
      dom.edgeBendLabel.textContent = describeEdgeBend(edge.viz.curveBend);
    }
    draw();
  }

  function stepEdgePull() {
    const factor = 0.01;
    const frozen = new Set(getSelectedTargets());
    const snapshot = deepCloneNodes();

    state.edges.forEach((edge) => {
      if (edge.hidden) return;
      if (endpointPair(edge) !== "tail:arrow") return;

      const sourceIndex = state.idToIndex.get(edge.source);
      const targetIndex = state.idToIndex.get(edge.target);
      const dx = snapshot[targetIndex].x - snapshot[sourceIndex].x;
      const dy = snapshot[targetIndex].y - snapshot[sourceIndex].y;

      if (!frozen.has(sourceIndex)) {
        state.nodes[sourceIndex].layout.x = clamp(state.nodes[sourceIndex].layout.x + factor * dx * Math.abs(dx), 0.02, 0.98);
        state.nodes[sourceIndex].layout.y = clamp(state.nodes[sourceIndex].layout.y + factor * dy * Math.abs(dy), 0.02, 0.98);
      }
      if (!frozen.has(targetIndex)) {
        state.nodes[targetIndex].layout.x = clamp(state.nodes[targetIndex].layout.x - factor * dx * Math.abs(dx), 0.02, 0.98);
        state.nodes[targetIndex].layout.y = clamp(state.nodes[targetIndex].layout.y - factor * dy * Math.abs(dy), 0.02, 0.98);
      }
    });

    draw();
    if (state.pullActive) requestAnimationFrame(stepEdgePull);
  }

  function stepVertexPush() {
    const factor = 0.001;
    const bandwidth = -0.1;
    const frozen = new Set(getSelectedTargets());
    const snapshot = deepCloneNodes();

    for (let i = 0; i < state.nodes.length; i += 1) {
      if (state.nodes[i].hidden) continue;
      for (let j = i + 1; j < state.nodes.length; j += 1) {
        if (state.nodes[j].hidden) continue;

        const dx = snapshot[j].x - snapshot[i].x;
        const dy = snapshot[j].y - snapshot[i].y;
        const moveX = factor * Math.sign(dx) * Math.exp((dx * dx) / bandwidth);
        const moveY = factor * Math.sign(dy) * Math.exp((dy * dy) / bandwidth);

        if (!frozen.has(i)) {
          state.nodes[i].layout.x = clamp(state.nodes[i].layout.x - moveX, 0.02, 0.98);
          state.nodes[i].layout.y = clamp(state.nodes[i].layout.y - moveY, 0.02, 0.98);
        }
        if (!frozen.has(j)) {
          state.nodes[j].layout.x = clamp(state.nodes[j].layout.x + moveX, 0.02, 0.98);
          state.nodes[j].layout.y = clamp(state.nodes[j].layout.y + moveY, 0.02, 0.98);
        }
      }
    }

    draw();
    if (state.pushActive) requestAnimationFrame(stepVertexPush);
  }

  function buildCurrentGraphPayload() {
    // Export the current graph state including layout, styling, and metadata.
    const originalInfo = state.originalGraph?.graph || {};
    return {
      schema_version: state.originalGraph?.schema_version || "1.1",
      graph: {
        name: state.graphName,
        graph_type: state.graphType,
        is_time_series: originalInfo.is_time_series || false,
        description: originalInfo.description || null,
        source_format: originalInfo.source_format || null,
        source_version: originalInfo.source_version || null,
        provenance: originalInfo.provenance || {}
      },
      nodes: state.nodes.map((node) => ({
        id: node.id,
        label: node.label,
        observed: node.observed,
        node_type: node.node_type,
        group: node.group || null,
        attributes: node.attributes,
        viz: {
          color: node.viz?.color || node.displayColor,
          size: node.size,
          shape: node.shape
        },
        layout: {
          x: Number(node.layout.x.toFixed(6)),
          y: Number(node.layout.y.toFixed(6))
        }
      })),
      edges: state.edges.map((edge) => ({
        source: edge.source,
        target: edge.target,
        endpoints: edge.endpoints,
        lag: edge.lag,
        weight: edge.weight,
        attributes: edge.attributes,
        viz: {
          color: edge.viz?.color || edge.displayColor,
          width: edge.width,
          curveMode: edge.viz?.curveMode,
          curveDirection: edge.viz?.curveDirection,
          curveStrength: edge.viz?.curveStrength,
          curveBend: edge.viz?.curveBend
        }
      })),
      metadata: cloneData(state.originalGraph?.metadata || {})
    };
  }

  function exportLayoutSnapshot() {
    // Save the current graph state as standalone JSON.
    const payload = buildCurrentGraphPayload();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "causal-viewer-v3-layout.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus("Exported current layout snapshot.");
  }

  function buildSessionPayload() {
    // Capture the graph plus workbench UI state for later restoration.
    return {
      session_version: "1.0",
      kind: "causal-viewer-v3-session",
      baseline_graph: cloneData(state.originalGraph || buildCurrentGraphPayload()),
      working_graph: buildCurrentGraphPayload(),
      files: {
        original_filename: state.originalFilename,
        current_filename: state.currentFilename
      },
      ui: {
        target_color: dom.targetColor.value,
        target_scope: dom.targetScope.value,
        selected_targets: getSelectedTargets().map((index) => state.nodes[index]?.id).filter(Boolean),
        threshold: Number(dom.thresholdSlider.value),
        edge_alpha_filter_mode: dom.edgeAlphaFilterMode.value,
        edge_width_filter_mode: dom.edgeWidthFilterMode.value,
        edge_label_mode: dom.edgeLabelMode.value,
        edge_label_size: Number(dom.edgeLabelSize.value),
        sidebar_width: Number(dom.widthSlider.value),
        export_type: dom.exportType.value,
        camera: {
          scale: state.scale,
          offset_x: state.offsetX,
          offset_y: state.offsetY
        },
        legend: dom.legendPanel.classList.contains("hidden")
          ? { visible: false }
          : {
              visible: true,
              title: dom.legendTitle.textContent || "",
              subtitle: dom.legendSubtitle.textContent || "",
              left: dom.legendPanel.style.left || "28px",
              top: dom.legendPanel.style.top || "28px",
              body_html: dom.legendBody.innerHTML
            }
      }
    };
  }

  function saveSession() {
    // Serialize the current session to disk.
    if (state.nodes.length === 0) {
      setStatus("Import a graph before saving a session.");
      return;
    }
    const payload = buildSessionPayload();
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const filenameBase = (state.currentFilename || state.graphName || "causal-viewer-v3-session")
      .replace(/[^a-z0-9-_]+/gi, "_");
    downloadBlob(`${filenameBase}_session.json`, blob);
    setStatus("Saved current session.");
  }

  function applySelectedTargetIds(targetIds) {
    const selectedIds = new Set(targetIds || []);
    for (const option of dom.targetSelect.options) {
      const index = Number(option.value);
      option.selected = selectedIds.has(state.nodes[index]?.id);
    }
  }

  function restoreLegendState(legendState) {
    // Restore legend visibility, content, and placement from a saved session.
    if (!legendState?.visible) {
      hideLegend();
      return;
    }
    dom.legendTitle.textContent = legendState.title || "Legend";
    dom.legendSubtitle.textContent = legendState.subtitle || "";
    dom.legendBody.innerHTML = legendState.body_html || "";
    dom.legendPanel.style.left = legendState.left || "28px";
    dom.legendPanel.style.top = legendState.top || "28px";
    dom.legendPanel.classList.remove("hidden");
  }

  async function loadSessionFromFile() {
    // Restore a saved session bundle back into the viewer.
    const file = dom.sessionFileInput.files?.[0];
    if (!file) {
      setStatus("Choose a session file first.");
      return;
    }

    const content = await readFileAsText(file);
    const payload = JSON.parse(content);
    if (payload.kind !== "causal-viewer-v3-session" || !payload.working_graph) {
      throw new Error("Unsupported session file.");
    }

    state.originalGraph = cloneData(payload.baseline_graph || payload.working_graph);
    state.originalFilename = payload.files?.original_filename || file.name;
    state.currentFilename = payload.files?.current_filename || file.name;

    normalizeGraph(cloneData(payload.working_graph));
    rebuildTargetOptions();

    const ui = payload.ui || {};
    dom.targetColor.value = ui.target_color || "#4f7cff";
    dom.targetScope.value = ui.target_scope || "all";
    dom.thresholdSlider.value = String(ui.threshold ?? 50);
    dom.thresholdLabel.textContent = `${dom.thresholdSlider.value}%`;
    dom.edgeAlphaFilterMode.value = ui.edge_alpha_filter_mode || "off";
    dom.edgeWidthFilterMode.value = ui.edge_width_filter_mode || "off";
    dom.edgeLabelMode.value = ui.edge_label_mode || "none";
    dom.edgeLabelSize.value = String(ui.edge_label_size ?? 12);
    dom.edgeLabelSizeLabel.textContent = `${dom.edgeLabelSize.value}px`;
    dom.exportType.value = ui.export_type || "png";
    setSidebarWidth(Number(ui.sidebar_width ?? dom.widthSlider.value));

    applySelectedTargetIds(ui.selected_targets || []);
    updateFilters();

    state.scale = clamp(ui.camera?.scale ?? 1, MIN_SCALE, MAX_SCALE);
    state.offsetX = Number(ui.camera?.offset_x ?? 0);
    state.offsetY = Number(ui.camera?.offset_y ?? 0);
    restoreLegendState(ui.legend);
    draw();

    setStatus(`Loaded session from ${file.name}.`);
    setImportStatus(`Session restored from ${file.name}.`);
  }

  function downloadBlob(filename, blob) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  function getExportCanvas() {
    // Render into an offscreen canvas so export does not depend on the visible DOM canvas.
    const exportCanvas = document.createElement("canvas");
    exportCanvas.width = dom.canvas.width;
    exportCanvas.height = dom.canvas.height;
    const exportCtx = exportCanvas.getContext("2d");
    renderScene(exportCtx);
    drawLegendToCanvas(exportCtx);
    return exportCanvas;
  }

  function exportCanvasAsSvgBlob(exportCanvas) {
    // Wrap the raster export in SVG for a lightweight SVG download path.
    const pngDataUrl = exportCanvas.toDataURL("image/png");
    const svg = [
      `<svg xmlns="http://www.w3.org/2000/svg" width="${exportCanvas.width}" height="${exportCanvas.height}" viewBox="0 0 ${exportCanvas.width} ${exportCanvas.height}">`,
      `<image href="${pngDataUrl}" width="${exportCanvas.width}" height="${exportCanvas.height}" />`,
      `</svg>`
    ].join("");
    return new Blob([svg], { type: "image/svg+xml" });
  }

  async function exportImage() {
    // Export the current view using the selected image format.
    const type = dom.exportType.value;
    const exportCanvas = getExportCanvas();
    const baseName = (state.graphName || "causal-viewer-v3").replace(/[^a-z0-9-_]+/gi, "_");

    if (type === "svg") {
      downloadBlob(`${baseName}.svg`, exportCanvasAsSvgBlob(exportCanvas));
      setStatus("Exported image as SVG.");
      return;
    }

    const mimeByType = {
      png: "image/png",
      jpeg: "image/jpeg",
      webp: "image/webp"
    };
    const mime = mimeByType[type] || "image/png";
    const blob = await new Promise((resolve) => exportCanvas.toBlob(resolve, mime, 1));
    if (!blob) {
      setStatus("Image export failed.");
      return;
    }
    const extension = type === "jpeg" ? "jpg" : type;
    downloadBlob(`${baseName}.${extension}`, blob);
    setStatus(`Exported image as ${extension.toUpperCase()}.`);
  }

  async function importGraphFromFile() {
    // Send the uploaded file to the Python import service for normalization.
    const file = dom.fileInput.files?.[0];
    if (!file) {
      setStatus("Choose a file to import first.");
      setImportStatus("No file selected.");
      return;
    }

    setStatus(`Importing ${file.name} via ${dom.parserSelect.value}...`);
    setImportStatus(`Reading ${file.name}...`);
    const content = await readFileAsText(file);
    let response;
    try {
      response = await fetch(SERVER_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          parser: dom.parserSelect.value,
          filename: file.name,
          content
        })
      });
    } catch (_) {
      throw new Error(
        "Import server unreachable. Launch the app with: python launcher.py"
      );
    }

    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "Import failed");
    }

    normalizeGraph(payload.graph);
    state.originalGraph = cloneData(payload.graph);
    state.originalFilename = file.name;
    state.currentFilename = file.name;
    hideLegend();
    rebuildTargetOptions();
    updateFilters();
    if (state.preferences.viewer.auto_fit_on_import) {
      fitViewToGraph();
      draw();
    }
    setStatus(`Imported ${payload.graph.graph.name} (${payload.graph.graph.graph_type}) from ${file.name}.`);
    setImportStatus(`Imported ${file.name} as ${dom.parserSelect.value}.`);
  }

  function resetView() {
    // Restore the original imported graph and reset transient viewer state.
    state.scale = 1;
    state.offsetX = 0;
    state.offsetY = 0;
    state.selectedIndex = -1;
    hideStyleEditor();

    if (state.originalGraph) {
      normalizeGraph(cloneData(state.originalGraph));
      state.currentFilename = state.originalFilename;
      rebuildTargetOptions();
      updateFilters();
      if (state.preferences.viewer.auto_fit_on_import) {
        fitViewToGraph();
      }
      hideLegend();
      setStatus("View and graph customizations reset.");
      setImportStatus(`Loaded ${state.graphName || "graph"} baseline state.`);
      return;
    }

    clearGraph();
    setStatus("View reset.");
    setImportStatus("No graph loaded.");
  }

  function bindEvents() {
    // Register control-panel, canvas, styling, legend, import, and session event handlers.
    dom.targetSelect.addEventListener("input", updateFilters);
    dom.targetColor.addEventListener("input", () => {
      updateFilters();
      syncPreferencesFromControls();
    });
    dom.targetScope.addEventListener("input", () => {
      updateFilters();
      syncPreferencesFromControls();
    });

    dom.thresholdSlider.addEventListener("input", () => {
      dom.thresholdLabel.textContent = `${dom.thresholdSlider.value}%`;
      updateFilters();
      syncPreferencesFromControls();
    });
    dom.edgeAlphaFilterMode.addEventListener("input", () => {
      draw();
      syncPreferencesFromControls();
    });
    dom.edgeWidthFilterMode.addEventListener("input", () => {
      draw();
      syncPreferencesFromControls();
    });
    dom.edgeLabelMode.addEventListener("input", () => {
      draw();
      syncPreferencesFromControls();
    });
    dom.edgeLabelSize.addEventListener("input", () => {
      dom.edgeLabelSizeLabel.textContent = `${dom.edgeLabelSize.value}px`;
      draw();
      syncPreferencesFromControls();
    });

    dom.widthSlider.addEventListener("input", () => {
      setSidebarWidth(Number(dom.widthSlider.value));
      syncPreferencesFromControls();
    });
    dom.exportType.addEventListener("input", syncPreferencesFromControls);

    dom.saveSessionBtn.addEventListener("click", saveSession);
    dom.loadSessionBtn.addEventListener("click", () => {
      dom.sessionFileInput.click();
    });
    dom.viewerGuideBtn.addEventListener("click", showViewerGuide);
    dom.exportImageBtn.addEventListener("click", () => {
      exportImage().catch((error) => setStatus(String(error)));
    });
    dom.exportLayoutBtn.addEventListener("click", exportLayoutSnapshot);
    dom.resetViewBtn.addEventListener("click", resetView);

    dom.importBtn.addEventListener("click", async () => {
      try {
        await importGraphFromFile();
      } catch (error) {
        setStatus(String(error));
        setImportStatus(String(error));
      }
    });
    dom.importLegendBtn.addEventListener("click", () => {
      loadLegendFromButton().catch((error) => setStatus(String(error)));
    });

    dom.fileInput.addEventListener("change", () => {
      const file = dom.fileInput.files?.[0];
      if (!file) {
        setImportStatus("No file selected.");
        return;
      }
      setImportStatus(`Selected ${file.name} for ${dom.parserSelect.value}.`);
    });

    dom.parserSelect.addEventListener("change", () => {
      const file = dom.fileInput.files?.[0];
      if (file) {
        setImportStatus(`Selected ${file.name} for ${dom.parserSelect.value}.`);
      } else {
        setImportStatus(`Parser set to ${dom.parserSelect.value}.`);
      }
    });

    dom.sessionFileInput.addEventListener("change", async () => {
      try {
        await loadSessionFromFile();
      } catch (error) {
        setStatus(String(error));
        setImportStatus(String(error));
      } finally {
        dom.sessionFileInput.value = "";
      }
    });

    dom.styleEditorClose.addEventListener("click", hideStyleEditor);
    dom.legendPanel.addEventListener("contextmenu", (event) => {
      event.preventDefault();
      event.stopPropagation();
      setStatus("Legend editing is not enabled yet. Current legend content comes from JSON, not markdown.");
    });
    dom.viewerGuideClose.addEventListener("click", hideViewerGuide);
    dom.viewerGuideModal.addEventListener("click", (event) => {
      if (event.target === dom.viewerGuideModal) {
        hideViewerGuide();
      }
    });
    [
      dom.nodeColorInput,
      dom.nodeAlphaInput,
      dom.nodeSizeInput,
      dom.nodeShapeInput,
      dom.edgeColorInput,
      dom.edgeAlphaInput,
      dom.edgeWidthInput,
      dom.edgeBendInput
    ].forEach((element) => element.addEventListener("input", applyStyleEditor));

    dom.edgeStep.addEventListener("pointerdown", () => {
      state.pullActive = true;
      stepEdgePull();
      setStatus("Running edge pull.");
    });
    dom.edgeStep.addEventListener("pointerup", () => {
      state.pullActive = false;
      setStatus("Edge pull stopped.");
    });
    dom.edgeStep.addEventListener("pointerleave", () => {
      state.pullActive = false;
    });

    dom.vertexStep.addEventListener("pointerdown", () => {
      state.pushActive = true;
      stepVertexPush();
      setStatus("Running vertex push.");
    });
    dom.vertexStep.addEventListener("pointerup", () => {
      state.pushActive = false;
      setStatus("Vertex push stopped.");
    });
    dom.vertexStep.addEventListener("pointerleave", () => {
      state.pushActive = false;
    });

    dom.divider.addEventListener("pointerdown", () => {
      state.resizeActive = true;
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    });

    document.addEventListener("pointermove", (event) => {
      if (state.resizeActive) {
        const nextPercent = (event.clientX / dom.container.clientWidth) * 100;
        setSidebarWidth(nextPercent);
      }

      if (state.selectedIndex !== -1) {
        const canvasPoint = eventToCanvasOffset(event);
        const pointer = screenToWorld(canvasPoint.x, canvasPoint.y);
        const width = ctx.canvas.width;
        const height = ctx.canvas.height;
        state.nodes[state.selectedIndex].layout.x = clamp((pointer.x + state.selectedDX) / width, 0.02, 0.98);
        state.nodes[state.selectedIndex].layout.y = clamp((pointer.y + state.selectedDY) / height, 0.02, 0.98);
        draw();
      }

      if (state.dragCanvas) {
        state.offsetX = event.clientX - state.dragStartX;
        state.offsetY = event.clientY - state.dragStartY;
        draw();
      }

      if (state.legendDragActive) {
        const rect = dom.canvasContainer.getBoundingClientRect();
        dom.legendPanel.style.left = `${Math.max(12, event.clientX - rect.left - state.legendDragOffsetX)}px`;
        dom.legendPanel.style.top = `${Math.max(12, event.clientY - rect.top - state.legendDragOffsetY)}px`;
      }
    });

    document.addEventListener("pointerup", () => {
      const resized = state.resizeActive;
      state.resizeActive = false;
      state.dragCanvas = false;
      state.selectedIndex = -1;
      state.legendDragActive = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      if (resized) syncPreferencesFromControls();
    });

    document.addEventListener("pointerdown", (event) => {
      if (dom.styleEditor.classList.contains("hidden")) return;
      if (!dom.styleEditor.contains(event.target)) hideStyleEditor();
    });

    dom.legendHeader.addEventListener("pointerdown", (event) => {
      const rect = dom.legendPanel.getBoundingClientRect();
      state.legendDragActive = true;
      state.legendDragOffsetX = event.clientX - rect.left;
      state.legendDragOffsetY = event.clientY - rect.top;
      event.preventDefault();
    });

    window.addEventListener("resize", resizeCanvas);
    window.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !dom.viewerGuideModal.classList.contains("hidden")) {
        hideViewerGuide();
      }
    });

    dom.canvas.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        if (state.dragCanvas) return;

        const worldX = (event.offsetX - state.offsetX) / state.scale;
        const worldY = (event.offsetY - state.offsetY) / state.scale;
        const delta = -Math.min(Math.max(event.deltaY, -20), 20);
        const zoom = Math.exp((delta * 0.1) / 100);
        const nextScale = clamp(state.scale * zoom, MIN_SCALE, MAX_SCALE);
        const appliedZoom = nextScale / state.scale;

        state.scale = nextScale;
        state.offsetX -= worldX * (appliedZoom - 1) * state.scale;
        state.offsetY -= worldY * (appliedZoom - 1) * state.scale;
        draw();
      },
      { passive: false }
    );

    dom.canvas.addEventListener("pointerdown", (event) => {
      if (event.button === 2) return;
      const hitIndex = findNodeIndexAt(event.offsetX, event.offsetY);
      if (hitIndex !== -1) {
        state.selectedIndex = hitIndex;
        const pointer = screenToWorld(event.offsetX, event.offsetY);
        const center = nodeCenter(state.nodes[hitIndex]);
        state.selectedDX = center.x - pointer.x;
        state.selectedDY = center.y - pointer.y;
        dom.canvas.setPointerCapture(event.pointerId);
        return;
      }

      const edgeIndex = findEdgeIndexAt(event.offsetX, event.offsetY);
      if (edgeIndex !== -1) {
        hideLegend();
        showStyleEditor("edge", edgeIndex, event.clientX, event.clientY);
        return;
      }

      state.dragCanvas = true;
      state.dragStartX = event.clientX - state.offsetX;
      state.dragStartY = event.clientY - state.offsetY;
      dom.canvas.setPointerCapture(event.pointerId);
    });

    dom.canvas.addEventListener("pointerup", (event) => {
      try {
        dom.canvas.releasePointerCapture(event.pointerId);
      } catch (_) {
        // Ignore completed gesture release failures.
      }
    });

    dom.canvas.addEventListener("contextmenu", handleCanvasContextMenu);
    dom.canvasContainer.addEventListener("contextmenu", handleCanvasContextMenu);
  }

  function init() {
    // Bootstrap preferences, events, and the initial empty viewer state.
    state.preferences = loadGlobalPreferences();
    bindEvents();
    applyGlobalPreferencesToControls();
    clearGraph();
    setStatus("No graph loaded.");
    setImportStatus("Choose a graph file to import, or load a saved session.");
    showViewerGuide();
  }

  init();
})();
