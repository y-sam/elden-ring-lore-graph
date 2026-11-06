const MAX_GRAPH_NODES = 60;
const urlState = new URLSearchParams(window.location.search);
const state = {
  rootEntityId: urlState.get("entity") || "artifact.elden-ring",
  activeEntityId: null,
  selectedEdgeId: null,
  includeDrafts: ["localhost", "127.0.0.1"].includes(window.location.hostname),
  nodes: new Map(),
  edges: new Map(),
  positions: new Map(),
  expansionChildren: new Map(),
  expandedNodes: new Set(),
  history: [],
  initialGraph: null,
  kindFilter: "all",
  evidenceFilter: "all",
  lastAnswer: null,
  drag: null,
  suppressNodeClick: false,
  canvasSize: { width: 900, height: 520 },
  zoom: 1,
  spoilerLevel: urlState.get("spoilers") || "minimal",
  journey: null,
  journeyEntries: new Map(),
  connection: null,
};

const $ = (selector) => document.querySelector(selector);
const svgNS = "http://www.w3.org/2000/svg";

function apiPath(path) {
  const separator = path.includes("?") ? "&" : "?";
  return `${path}${separator}include_drafts=${state.includeDrafts}`;
}

async function api(path) {
  const response = await fetch(path, {
    headers: { Accept: "application/json" },
    signal: AbortSignal.timeout(15000),
  });
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function readable(value = "") {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function checkStatus() {
  const status = $("#api-status");
  try {
    await api("/ready");
    status.classList.add("is-online");
    status.lastChild.textContent = " Connected";
  } catch {
    status.classList.remove("is-online");
    status.lastChild.textContent = " Offline";
  }
}

function evidenceMarkup(items) {
  if (!items.length) return '<p class="no-evidence">No linked evidence is available yet.</p>';
  return items.map((item) => `
    <details class="evidence">
      <summary>${escapeHtml(item.locator)}</summary>
      <p>${escapeHtml(localizedEvidenceSummary(item))}</p>
      <cite>${escapeHtml(item.source_title)} · ${escapeHtml(item.authority_tier)}</cite>
    </details>`).join("");
}

function localizedEvidenceSummary(item, language = $("#answer-language")?.value) {
  return item.localized_summaries?.[language] || item.summary_en;
}

function claimContext(claim) {
  return [
    claim.role ? `Role: ${claim.role}` : "",
    claim.temporal_scope ? `Time: ${readable(claim.temporal_scope)}` : "",
    claim.qualifier || "",
  ].filter(Boolean).join(" · ");
}

function renderInspector(entity) {
  const claims = entity.claims.length
    ? entity.claims.map((claim) => {
      const counterpart = claim.direction === "outgoing" ? claim.object : claim.subject;
      return `
        <button class="claim-card" type="button" data-claim-id="${escapeHtml(claim.id)}">
          <header><span class="predicate">${escapeHtml(readable(claim.predicate))}</span><span class="direction">${claim.direction}</span></header>
          <span class="claim-target">${counterpart ? escapeHtml(counterpart.canonical_name) : "—"}</span>
          ${claimContext(claim) ? `<small class="claim-context">${escapeHtml(claimContext(claim))}</small>` : ""}
          <span class="claim-meta"><span class="chip">${escapeHtml(readable(claim.evidence_level))}</span><span class="chip">${escapeHtml(claim.confidence)} confidence</span></span>
        </button>`;
    }).join("")
    : '<p class="empty-state">No reviewed claims are visible for this entity.</p>';
  $("#entity-inspector").innerHTML = `
    <p class="entity-kind">${escapeHtml(entity.kind)}</p>
    <h2>${escapeHtml(entity.canonical_name)}</h2>
    <p class="entity-id">${escapeHtml(entity.id)}</p>
    <a class="inspector-action" href="/entity.html?id=${encodeURIComponent(entity.id)}">Open permanent profile</a>
    <button class="inspector-action" type="button" data-expand-entity="${escapeHtml(entity.id)}">Expand this entity</button>
    <button class="inspector-action" type="button" data-connect-entity="${escapeHtml(entity.id)}">Find a connection</button>
    <section class="suggested-questions" data-suggested-for="${escapeHtml(entity.id)}"><p class="eyebrow">Questions to explore</p><p class="empty-state">Loading suggestions…</p></section>
    <div class="claim-list">${claims}</div>`;
  $("#entity-inspector").querySelector("[data-expand-entity]").addEventListener("click", () => expandNode(entity.id));
  $("#entity-inspector").querySelector("[data-connect-entity]").addEventListener("click", () => startConnectionFrom(entity));
  $("#entity-inspector").querySelectorAll("[data-claim-id]").forEach((button) => button.addEventListener("click", () => selectEdge(button.dataset.claimId)));
  loadSuggestedQuestions(entity.id);
}

function renderDiscoveryInspector(entity, entry) {
  const nextSteps = entry.next_entity_ids.map((entityId) => {
    const node = state.nodes.get(entityId);
    const label = node?.canonical_name || readable(entityId.split(".").at(-1));
    return `<button type="button" data-next-entity="${escapeHtml(entityId)}">${escapeHtml(label)}</button>`;
  }).join("");
  $("#entity-inspector").innerHTML = `
    <p class="entity-kind">${escapeHtml(entity.kind)} · guided introduction</p>
    <h2>${escapeHtml(entity.canonical_name)}</h2>
    <p class="discovery-introduction">${escapeHtml(entry.introduction)}</p>
    <div class="discovery-inspector-actions">
      <button class="inspector-action" type="button" data-ask-entity>Ask about this</button>
      <button class="inspector-action" type="button" data-expand-entity="${escapeHtml(entity.id)}">Expand this entity</button>
      <button class="inspector-action" type="button" data-connect-entity="${escapeHtml(entity.id)}">Find a connection</button>
      <a class="inspector-action" href="/entity.html?id=${encodeURIComponent(entity.id)}">Open permanent profile</a>
    </div>
    <section class="suggested-questions" data-suggested-for="${escapeHtml(entity.id)}"><p class="eyebrow">Questions to explore</p><p class="empty-state">Loading suggestions…</p></section>
    ${nextSteps ? `<section class="discovery-next"><p class="eyebrow">Continue exploring</p><div>${nextSteps}</div></section>` : ""}
    <p class="spoiler-note">Expanding the graph may reveal relationships beyond this guided introduction.</p>`;
  $("#entity-inspector").querySelector("[data-ask-entity]").addEventListener("click", () => {
    $("#question-input").value = entry.prompt;
    askArchive(entry.prompt);
    $("#question-form").scrollIntoView({ behavior: "smooth", block: "center" });
  });
  $("#entity-inspector").querySelector("[data-expand-entity]").addEventListener("click", () => expandNode(entity.id));
  $("#entity-inspector").querySelector("[data-connect-entity]").addEventListener("click", () => startConnectionFrom(entity));
  $("#entity-inspector").querySelectorAll("[data-next-entity]").forEach((button) => button.addEventListener("click", () => {
    if (state.nodes.has(button.dataset.nextEntity)) selectNode(button.dataset.nextEntity);
    else loadRoot(button.dataset.nextEntity);
  }));
  loadSuggestedQuestions(entity.id);
}

async function loadSuggestedQuestions(entityId) {
  const container = $(`[data-suggested-for="${CSS.escape(entityId)}"]`);
  if (!container) return;
  try {
    const data = await api(apiPath(`/api/v1/entities/${encodeURIComponent(entityId)}/questions`));
    if (!document.body.contains(container)) return;
    container.innerHTML = `<p class="eyebrow">Questions to explore</p><div>${data.items.map((item) => `<button type="button" data-suggested-question="${escapeHtml(item.question)}">${escapeHtml(item.question)}</button>`).join("")}</div>`;
    container.querySelectorAll("[data-suggested-question]").forEach((button) => button.addEventListener("click", () => {
      $("#question-input").value = button.dataset.suggestedQuestion;
      askArchive(button.dataset.suggestedQuestion);
      $("#question-form").scrollIntoView({ behavior: "smooth", block: "center" });
    }));
  } catch {
    container.innerHTML = '<p class="eyebrow">Questions to explore</p><p class="empty-state">Suggestions are temporarily unavailable.</p>';
  }
}

function renderClaimInspector(claim) {
  $("#entity-inspector").innerHTML = `
    <button class="inspector-back" type="button">← Back to selected entity</button>
    <p class="entity-kind">Relationship claim</p>
    <h2>${escapeHtml(readable(claim.predicate))}</h2>
    <p class="entity-id">${escapeHtml(claim.id)}</p>
    <div class="relationship-route">
      <button type="button" data-route-entity="${escapeHtml(claim.subject.id)}">${escapeHtml(claim.subject.canonical_name)}</button>
      <span>→</span>
      ${claim.object ? `<button type="button" data-route-entity="${escapeHtml(claim.object.id)}">${escapeHtml(claim.object.canonical_name)}</button>` : "—"}
    </div>
    <div class="claim-meta">
      <span class="chip">${escapeHtml(readable(claim.evidence_level))}</span>
      <span class="chip">${escapeHtml(claim.confidence)} confidence</span>
      <span class="chip">${escapeHtml(claim.review_status)}</span>
    </div>
    ${claimContext(claim) ? `<p class="claim-context">${escapeHtml(claimContext(claim))}</p>` : ""}
    <div class="evidence-list"><h3>Evidence</h3>${evidenceMarkup(claim.evidence)}</div>`;
  $(".inspector-back").addEventListener("click", () => selectNode(state.activeEntityId));
  $("#entity-inspector").querySelectorAll("[data-route-entity]").forEach((button) => button.addEventListener("click", () => selectNode(button.dataset.routeEntity)));
}

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(svgNS, name);
  Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, value));
  return element;
}

function initialPosition(index, count) {
  if (index === 0) return { x: 450, y: 260 };
  const angle = ((index - 1) / Math.max(count - 1, 1)) * Math.PI * 2 - Math.PI / 2;
  return { x: 450 + Math.cos(angle) * 285, y: 260 + Math.sin(angle) * 180 };
}

function positionNewNodes(parentId, nodeIds) {
  const parent = state.positions.get(parentId) || { x: 450, y: 260 };
  nodeIds.forEach((id, index) => {
    if (state.positions.has(id)) return;
    const angle = ((index + 1) / (nodeIds.length + 1)) * Math.PI * 1.5 - Math.PI * 0.75;
    state.positions.set(id, {
      x: Math.min(830, Math.max(70, parent.x + Math.cos(angle) * 185)),
      y: Math.min(455, Math.max(65, parent.y + Math.sin(angle) * 145)),
    });
  });
}

function layoutStorageKey() { return `lore-graph-layout:${state.rootEntityId}`; }

function saveLayout() {
  const positions = Object.fromEntries(state.positions);
  localStorage.setItem(layoutStorageKey(), JSON.stringify({ positions, canvasSize: state.canvasSize }));
}

function restoreLayout() {
  try {
    const saved = JSON.parse(localStorage.getItem(layoutStorageKey()) || "null");
    if (!saved?.positions) return;
    Object.entries(saved.positions).forEach(([id, position]) => {
      if (state.nodes.has(id)) state.positions.set(id, position);
    });
    if (saved.canvasSize) state.canvasSize = saved.canvasSize;
  } catch { localStorage.removeItem(layoutStorageKey()); }
}

function arrangeGraph() {
  const graph = visibleGraph();
  if (!graph.nodes.length) return;
  state.history.push(graphSnapshot());
  const columns = Math.max(4, Math.ceil(Math.sqrt(graph.nodes.length * 1.6)));
  const rows = Math.ceil(graph.nodes.length / columns);
  state.canvasSize = {
    width: Math.max(900, columns * 165),
    height: Math.max(520, rows * 135),
  };
  const ordered = [...graph.nodes].sort((a, b) => {
    if (a.id === state.rootEntityId) return -1;
    if (b.id === state.rootEntityId) return 1;
    return a.canonical_name.localeCompare(b.canonical_name);
  });
  ordered.forEach((node, index) => {
    const column = index % columns;
    const row = Math.floor(index / columns);
    state.positions.set(node.id, { x: 82 + column * 165, y: 72 + row * 135 });
  });
  saveLayout();
  renderGraph();
}

function graphPoint(svg, event) {
  const bounds = svg.getBoundingClientRect();
  return {
    x: Math.max(55, Math.min(state.canvasSize.width - 55, (event.clientX - bounds.left) * state.canvasSize.width / bounds.width)),
    y: Math.max(55, Math.min(state.canvasSize.height - 55, (event.clientY - bounds.top) * state.canvasSize.height / bounds.height)),
  };
}

function updateGraphGeometry(svg, nodeId, position) {
  const node = svg.querySelector(`[data-node-id="${CSS.escape(nodeId)}"]`);
  if (node) node.setAttribute("transform", `translate(${position.x} ${position.y})`);
  svg.querySelectorAll(`[data-edge-source="${CSS.escape(nodeId)}"], [data-edge-target="${CSS.escape(nodeId)}"]`).forEach((group) => {
    const start = state.positions.get(group.dataset.edgeSource);
    const end = state.positions.get(group.dataset.edgeTarget);
    group.querySelectorAll("line").forEach((line) => {
      line.setAttribute("x1", start.x); line.setAttribute("y1", start.y);
      line.setAttribute("x2", end.x); line.setAttribute("y2", end.y);
    });
    const label = group.querySelector("text");
    label.setAttribute("x", (start.x + end.x) / 2);
    label.setAttribute("y", (start.y + end.y) / 2 - 7);
  });
}

function visibleGraph() {
  const edges = [...state.edges.values()].filter((edge) => state.evidenceFilter === "all" || edge.evidence_level === state.evidenceFilter);
  const connectedIds = new Set(edges.flatMap((edge) => [edge.source, edge.target]));
  const nodes = [...state.nodes.values()].filter((node) => {
    const kindMatches = state.kindFilter === "all" || node.kind === state.kindFilter;
    const required = node.id === state.rootEntityId || node.id === state.activeEntityId;
    return kindMatches && (state.evidenceFilter === "all" || connectedIds.has(node.id) || required);
  });
  const nodeIds = new Set(nodes.map((node) => node.id));
  return { nodes, edges: edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target)) };
}

function renderGraph() {
  const canvas = $("#graph-canvas");
  const graph = visibleGraph();
  $("#graph-stats").textContent = `${graph.nodes.length} nodes · ${graph.edges.length} claims`;
  $("#undo-graph").disabled = !state.history.length;
  $("#collapse-node").disabled = !state.expansionChildren.has(state.activeEntityId);
  $("#hide-node").disabled = !state.activeEntityId || state.activeEntityId === state.rootEntityId;
  if (!graph.nodes.length) {
    canvas.innerHTML = '<p class="empty-state">No relationships match these filters.</p>';
    return;
  }
  const svg = svgElement("svg", { viewBox: `0 0 ${state.canvasSize.width} ${state.canvasSize.height}`, role: "img", "aria-label": "Expandable relationship graph" });
  svg.style.width = `${state.canvasSize.width * state.zoom}px`;
  svg.style.height = `${state.canvasSize.height * state.zoom}px`;
  graph.edges.forEach((edge) => {
    const start = state.positions.get(edge.source);
    const end = state.positions.get(edge.target);
    if (!start || !end) return;
    const inferred = !["explicit", "synthesis"].includes(edge.evidence_level);
    const group = svgElement("g", { class: `edge-group${edge.id === state.selectedEdgeId ? " selected" : ""}`, tabindex: "0", role: "button", "aria-label": `Inspect ${readable(edge.predicate)} claim`, "data-edge-source": edge.source, "data-edge-target": edge.target });
    group.append(svgElement("line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, class: "edge-hit" }));
    group.append(svgElement("line", { x1: start.x, y1: start.y, x2: end.x, y2: end.y, class: `graph-edge${inferred ? " inferred" : ""}` }));
    const label = svgElement("text", { x: (start.x + end.x) / 2, y: (start.y + end.y) / 2 - 7, class: "edge-label", "text-anchor": "middle" });
    label.textContent = readable(edge.predicate);
    group.append(label);
    const inspect = () => selectEdge(edge.id);
    group.addEventListener("click", inspect);
    group.addEventListener("keydown", (event) => { if (["Enter", " "].includes(event.key)) { event.preventDefault(); inspect(); } });
    svg.append(group);
  });
  graph.nodes.forEach((node) => {
    const position = state.positions.get(node.id);
    const isRoot = node.id === state.rootEntityId;
    const selected = node.id === state.activeEntityId;
    const expanded = state.expandedNodes.has(node.id);
    const group = svgElement("g", { class: `graph-node${isRoot ? " root" : ""}${selected ? " selected" : ""}${expanded ? " expanded" : ""}`, tabindex: "0", role: "button", "aria-label": `Select ${node.canonical_name}; drag to rearrange; double-click to expand`, "data-node-id": node.id, transform: `translate(${position.x} ${position.y})` });
    group.append(svgElement("circle", { cx: 0, cy: 0, r: isRoot ? 58 : 48 }));
    const label = svgElement("text", { x: 0, y: -2, class: "node-label" });
    const words = node.canonical_name.split(" ");
    const midpoint = Math.ceil(words.length / 2);
    (words.length > 2 ? [words.slice(0, midpoint).join(" "), words.slice(midpoint).join(" ")] : [node.canonical_name]).forEach((line, index) => {
      const span = svgElement("tspan", { x: 0, dy: index === 0 ? 0 : 15 });
      span.textContent = line;
      label.append(span);
    });
    group.append(label);
    const kind = svgElement("text", { x: 0, y: 29, class: "node-kind" });
    kind.textContent = `${node.kind.toUpperCase()}${expanded ? " · EXPANDED" : ""}`;
    group.append(kind);
    group.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      state.drag = { nodeId: node.id, svg, start: graphPoint(svg, event), moved: false };
      group.setPointerCapture?.(event.pointerId);
      group.classList.add("dragging");
    });
    group.addEventListener("pointermove", (event) => {
      if (!state.drag || state.drag.nodeId !== node.id) return;
      const point = graphPoint(svg, event);
      if (Math.hypot(point.x - state.drag.start.x, point.y - state.drag.start.y) > 3) state.drag.moved = true;
      state.positions.set(node.id, point);
      updateGraphGeometry(svg, node.id, point);
    });
    group.addEventListener("pointerup", () => {
      state.suppressNodeClick = Boolean(state.drag?.moved);
      state.drag = null;
      group.classList.remove("dragging");
      saveLayout();
    });
    group.addEventListener("click", () => {
      if (state.suppressNodeClick) { state.suppressNodeClick = false; return; }
      selectNode(node.id);
    });
    group.addEventListener("dblclick", () => expandNode(node.id));
    group.addEventListener("keydown", (event) => {
      if (event.key === "Enter") selectNode(node.id);
      if (["+", " "].includes(event.key)) { event.preventDefault(); expandNode(node.id); }
    });
    svg.append(group);
  });
  canvas.replaceChildren(svg);
}

function graphSnapshot() {
  return {
    nodes: new Map(state.nodes), edges: new Map(state.edges), positions: new Map(state.positions),
    expansionChildren: new Map([...state.expansionChildren].map(([key, value]) => [key, new Set(value)])),
    expandedNodes: new Set(state.expandedNodes), activeEntityId: state.activeEntityId,
  };
}

function restoreSnapshot(snapshot) {
  Object.assign(state, snapshot);
  state.selectedEdgeId = null;
  renderGraph();
  selectNode(state.activeEntityId, false);
  updateUrl();
}

function mergeGraph(graph, parentId) {
  const newNodeIds = graph.nodes.filter((node) => !state.nodes.has(node.id)).map((node) => node.id);
  graph.nodes.forEach((node) => state.nodes.set(node.id, node));
  graph.edges.forEach((edge) => state.edges.set(edge.id, edge));
  positionNewNodes(parentId, newNodeIds);
  state.expansionChildren.set(parentId, new Set(newNodeIds));
  state.expandedNodes.add(parentId);
}

async function selectNode(entityId, rerender = true) {
  if (!entityId) return;
  state.activeEntityId = entityId;
  state.selectedEdgeId = null;
  if (rerender) renderGraph();
  $("#entity-inspector").innerHTML = '<div class="skeleton-block"></div><div class="skeleton-line"></div><div class="skeleton-line short"></div>';
  try {
    const entity = await api(apiPath(`/api/v1/entities/${encodeURIComponent(entityId)}`));
    const journeyEntry = state.journeyEntries.get(entityId);
    if (journeyEntry) renderDiscoveryInspector(entity, journeyEntry);
    else renderInspector(entity);
  } catch {
    $("#entity-inspector").innerHTML = '<p class="empty-state">This entity could not be loaded.</p>';
  }
}

async function selectEdge(claimId) {
  state.selectedEdgeId = claimId;
  renderGraph();
  $("#entity-inspector").innerHTML = '<div class="skeleton-block"></div><div class="skeleton-line"></div>';
  try {
    renderClaimInspector(await api(apiPath(`/api/v1/claims/${encodeURIComponent(claimId)}`)));
  } catch {
    $("#entity-inspector").innerHTML = '<p class="empty-state">This claim could not be loaded.</p>';
  }
}

async function revealAnswerClaim(claim) {
  await loadRoot(claim.subject.id);
  await selectEdge(claim.id);
}

async function loadRoot(entityId, restoreExpanded = []) {
  state.journey = null;
  state.journeyEntries.clear();
  state.connection = null;
  state.rootEntityId = entityId;
  state.activeEntityId = entityId;
  state.selectedEdgeId = null;
  state.nodes.clear(); state.edges.clear(); state.positions.clear();
  state.expansionChildren.clear(); state.expandedNodes.clear(); state.history = [];
  state.canvasSize = { width: 900, height: 520 };
  try {
    const graph = await api(apiPath(`/api/v1/entities/${encodeURIComponent(entityId)}/subgraph?depth=1&limit=30`));
    const ordered = [...graph.nodes].sort((a, b) => a.id === entityId ? -1 : b.id === entityId ? 1 : a.canonical_name.localeCompare(b.canonical_name));
    ordered.forEach((node, index) => { state.nodes.set(node.id, node); state.positions.set(node.id, initialPosition(index, ordered.length)); });
    restoreLayout();
    graph.edges.forEach((edge) => state.edges.set(edge.id, edge));
    state.initialGraph = graphSnapshot();
    renderGraph();
    await selectNode(entityId, false);
    for (const expandedId of restoreExpanded) if (state.nodes.has(expandedId)) await expandNode(expandedId, false);
    updateUrl();
  } catch {
    $("#graph-canvas").innerHTML = '<p class="empty-state">The graph could not be loaded.</p>';
  }
}

async function loadDiscoveryCollections() {
  const container = $("#discovery-collections");
  container.innerHTML = '<p class="empty-state">Loading guided paths…</p>';
  try {
    const data = await api(`/api/v1/discovery?spoiler_level=${encodeURIComponent(state.spoilerLevel)}`);
    container.innerHTML = data.collections.map((collection) => `
      <button class="discovery-card${state.journey?.id === collection.id ? " is-active" : ""}" type="button" data-journey="${escapeHtml(collection.id)}">
        <span>${escapeHtml(readable(collection.spoiler_level))}</span>
        <strong>${escapeHtml(collection.title)}</strong>
        <small>${escapeHtml(collection.description)}</small>
        <em>${collection.entity_count} starting points →</em>
      </button>`).join("");
    container.querySelectorAll("[data-journey]").forEach((button) => button.addEventListener("click", () => loadJourney(button.dataset.journey)));
  } catch {
    container.innerHTML = '<p class="empty-state">Guided paths are temporarily unavailable.</p>';
  }
}

async function loadJourney(collectionId) {
  const status = $("#discovery-status");
  status.hidden = false;
  status.textContent = "Opening the guided graph…";
  try {
    const journey = await api(`/api/v1/discovery/${encodeURIComponent(collectionId)}?spoiler_level=${encodeURIComponent(state.spoilerLevel)}`);
    state.journey = journey;
    state.journeyEntries = new Map(journey.entries.map((entry) => [entry.entity.id, entry]));
    state.rootEntityId = journey.default_entity_id;
    state.activeEntityId = journey.default_entity_id;
    state.selectedEdgeId = null;
    state.nodes.clear(); state.edges.clear(); state.positions.clear();
    state.expansionChildren.clear(); state.expandedNodes.clear(); state.history = [];
    state.canvasSize = { width: 900, height: 520 };
    const ordered = [...journey.entries].sort((a, b) => a.entity.id === journey.default_entity_id ? -1 : b.entity.id === journey.default_entity_id ? 1 : 0);
    ordered.forEach((entry, index) => {
      state.nodes.set(entry.entity.id, entry.entity);
      state.positions.set(entry.entity.id, initialPosition(index, ordered.length));
    });
    journey.edges.forEach((edge) => state.edges.set(edge.id, edge));
    state.initialGraph = graphSnapshot();
    renderGraph();
    await selectNode(journey.default_entity_id, false);
    updateUrl();
    activateView("graph");
    await loadDiscoveryCollections();
    status.textContent = `${journey.title}: select any node to begin.`;
    $("#graph-view").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch {
    status.textContent = "This guided path could not be opened with the selected spoiler setting.";
  }
}

async function expandNode(entityId = state.activeEntityId, recordHistory = true) {
  if (!entityId || state.nodes.size >= MAX_GRAPH_NODES) return;
  if (recordHistory) state.history.push(graphSnapshot());
  try {
    const graph = await api(apiPath(`/api/v1/entities/${encodeURIComponent(entityId)}/subgraph?depth=1&limit=30`));
    mergeGraph(graph, entityId);
    state.activeEntityId = entityId;
    renderGraph();
    await selectNode(entityId, false);
    updateUrl();
  } catch {
    if (recordHistory) state.history.pop();
  }
}

function collectBranch(parentId, collected = new Set()) {
  for (const childId of state.expansionChildren.get(parentId) || []) {
    if (childId === state.rootEntityId || collected.has(childId)) continue;
    collected.add(childId);
    collectBranch(childId, collected);
  }
  return collected;
}

function collapseSelected() {
  const parentId = state.activeEntityId;
  if (!state.expansionChildren.has(parentId)) return;
  state.history.push(graphSnapshot());
  const removals = collectBranch(parentId);
  removals.forEach((id) => { state.nodes.delete(id); state.positions.delete(id); state.expansionChildren.delete(id); state.expandedNodes.delete(id); });
  [...state.edges].forEach(([id, edge]) => { if (removals.has(edge.source) || removals.has(edge.target)) state.edges.delete(id); });
  state.expansionChildren.delete(parentId); state.expandedNodes.delete(parentId);
  renderGraph(); updateUrl();
}

function hideSelected() {
  const entityId = state.activeEntityId;
  if (!entityId || entityId === state.rootEntityId) return;
  state.history.push(graphSnapshot());
  state.nodes.delete(entityId);
  state.positions.delete(entityId);
  state.expansionChildren.delete(entityId);
  state.expandedNodes.delete(entityId);
  state.expansionChildren.forEach((children) => children.delete(entityId));
  [...state.edges].forEach(([id, edge]) => {
    if (edge.source === entityId || edge.target === entityId) state.edges.delete(id);
  });
  state.activeEntityId = state.rootEntityId;
  renderGraph();
  selectNode(state.rootEntityId, false);
  updateUrl();
}

function undoGraph() {
  const snapshot = state.history.pop();
  if (snapshot) restoreSnapshot(snapshot);
}

function resetGraph() {
  if (!state.initialGraph) return;
  state.history.push(graphSnapshot());
  restoreSnapshot({ ...state.initialGraph, activeEntityId: state.rootEntityId });
}

function updateUrl() {
  const params = state.connection
    ? new URLSearchParams(state.connection.params)
    : new URLSearchParams();
  if (state.connection) {
    params.set("view", "graph");
    params.set("path", String(state.connection.pathIndex || 0));
  } else if (state.journey) {
    params.set("journey", state.journey.id);
    params.set("spoilers", state.spoilerLevel);
  } else params.set("entity", state.rootEntityId);
  if (state.expandedNodes.size) params.set("expanded", [...state.expandedNodes].join(","));
  window.history.replaceState(null, "", `${window.location.pathname}?${params}`);
}

async function searchArchive(query) {
  const container = $("#search-results");
  container.hidden = false;
  container.innerHTML = '<p class="empty-state">Searching the archive…</p>';
  try {
    const data = await api(apiPath(`/api/v1/search?q=${encodeURIComponent(query)}&limit=8`));
    container.innerHTML = data.items.length ? data.items.map((item) => item.result_type === "entity" ? `
      <button class="search-result" type="button" data-entity-id="${escapeHtml(item.id)}"><strong>${escapeHtml(item.title)}</strong><span>Entity</span></button>` : `
      <div class="search-result evidence"><strong>${escapeHtml(item.title)}</strong><span>Evidence</span><p>${escapeHtml(item.summary || "")}</p></div>`).join("") : '<p class="empty-state">No matching records.</p>';
    container.querySelectorAll("[data-entity-id]").forEach((button) => button.addEventListener("click", () => {
      container.hidden = true; activateView("graph"); loadRoot(button.dataset.entityId); $("#graph-view").scrollIntoView({ behavior: "smooth", block: "start" });
    }));
  } catch { container.innerHTML = '<p class="empty-state">Search is temporarily unavailable.</p>'; }
}

function claimAnswerMarkup(claim) {
  const target = claim.object ? claim.object.canonical_name : "—";
  return `<button class="answer-claim" type="button" data-answer-claim="${escapeHtml(claim.id)}">
    <span>${escapeHtml(readable(claim.predicate))}</span>
    <strong>${escapeHtml(claim.subject.canonical_name)} → ${escapeHtml(target)}</strong>
    <small>${escapeHtml(readable(claim.evidence_level))} · ${escapeHtml(claim.confidence)} confidence${claimContext(claim) ? ` · ${escapeHtml(claimContext(claim))}` : ""}</small>
  </button>`;
}

function renderAnswer(data) {
  state.lastAnswer = data;
  const result = $("#answer-result");
  result.hidden = false;
  const explicit = data.explicit_claims.map(claimAnswerMarkup).join("");
  const inferred = data.inferred_claims.map(claimAnswerMarkup).join("");
  const supporting = data.supporting_claims.map(claimAnswerMarkup).join("");
  const citations = data.citations.map((citation, index) => `
    <details class="answer-citation">
      <summary>[${index + 1}] ${escapeHtml(citation.locator)}</summary>
      <p>${escapeHtml(localizedEvidenceSummary(citation, data.language))}</p>
      <cite>${escapeHtml(citation.source_title)} · ${escapeHtml(citation.authority_tier)} · ${escapeHtml(readable(citation.verification_status))}</cite>
    </details>`).join("");
  const entities = data.matched_entities.map((entity) => `<button type="button" data-answer-entity="${escapeHtml(entity.id)}">${escapeHtml(entity.canonical_name)}</button>`).join("");
  const generationLabel = data.generation_mode === "generated"
    ? `${readable(data.generator)} generated`
    : data.generation_mode === "fallback"
      ? "Deterministic fallback"
      : "Deterministic";
  result.innerHTML = `
    <header><span class="answer-status ${escapeHtml(data.status)}">${escapeHtml(data.status)}</span><span>${escapeHtml(readable(data.intent))} · ${escapeHtml(data.language)} · ${escapeHtml(generationLabel)}</span></header>
    <p class="answer-copy">${escapeHtml(data.answer)}</p>
    <p class="answer-provenance">Grounded in ${data.reviewed_claim_count} reviewed of ${data.grounded_claim_count} selected claims · ${data.verified_evidence_count} verified evidence records.</p>
    ${entities ? `<div class="answer-entities">${entities}</div>` : ""}
    ${(explicit || inferred || supporting || citations) ? `<details class="answer-grounding" ${data.generation_mode === "generated" ? "" : "open"}><summary>Inspect the evidence view: ${data.grounded_claim_count} claims · ${data.citations.length} citations</summary>
      ${explicit ? `<section><h3>Supported relationships</h3><div class="answer-claims">${explicit}</div></section>` : ""}
      ${inferred ? `<section class="answer-inference"><h3>Inference and uncertainty</h3><div class="answer-claims">${inferred}</div></section>` : ""}
      ${supporting ? `<section class="answer-path"><h3>Connection path</h3><p>These claims connect the named entity to the answer through one intermediate node.</p><div class="answer-claims">${supporting}</div></section>` : ""}
      ${citations ? `<section><h3>Evidence trail</h3>${citations}</section>` : ""}
    </details>` : ""}
    ${data.limitations.length ? `<ul class="answer-limitations">${data.limitations.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>` : ""}`;
  result.insertAdjacentHTML("beforeend", `
    <form class="feedback-form" id="feedback-form">
      <h3>Was this answer trustworthy and useful?</h3>
      <div class="feedback-ratings">
        <label><input type="radio" name="rating" value="helpful" required> Helpful</label>
        <label><input type="radio" name="rating" value="mixed"> Mixed</label>
        <label><input type="radio" name="rating" value="not_helpful"> Not helpful</label>
      </div>
      <select name="reason" aria-label="Feedback reason">
        <option value="">Reason (optional)</option>
        <option value="accurate">Accurate</option><option value="clear">Clear</option>
        <option value="missing_context">Missing context</option><option value="wrong_fact">Wrong fact</option>
        <option value="weak_evidence">Weak evidence</option><option value="translation">Translation issue</option>
        <option value="other">Other</option>
      </select>
      <textarea name="comment" maxlength="1000" rows="2" placeholder="Add a comment for the editorial team (optional)"></textarea>
      <button type="submit">Send feedback</button><span class="feedback-status" role="status"></span>
    </form>`);
  result.querySelectorAll("[data-answer-entity]").forEach((button) => button.addEventListener("click", () => {
    activateView("graph"); loadRoot(button.dataset.answerEntity); $("#graph-view").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  result.querySelectorAll("[data-answer-claim]").forEach((button) => button.addEventListener("click", async () => {
    const claims = [...data.explicit_claims, ...data.inferred_claims, ...data.supporting_claims];
    const claim = claims.find((item) => item.id === button.dataset.answerClaim);
    activateView("graph");
    if (claim) await revealAnswerClaim(claim); else await selectEdge(button.dataset.answerClaim);
    $("#graph-view").scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  $("#feedback-form").addEventListener("submit", submitFeedback);
}

async function submitFeedback(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const formData = new FormData(form);
  const status = form.querySelector(".feedback-status");
  const answer = state.lastAnswer;
  status.textContent = "Sending…";
  const claimIds = [...answer.explicit_claims, ...answer.inferred_claims, ...answer.supporting_claims].map((claim) => claim.id);
  try {
    const response = await fetch("/api/v1/feedback", {
      method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({
        answer_id: answer.answer_id, question: answer.question, language: answer.language,
        rating: formData.get("rating"), reason: formData.get("reason") || null,
        comment: formData.get("comment")?.trim() || null, claim_ids: claimIds,
      }),
    });
    if (!response.ok) throw new Error("feedback failed");
    form.querySelectorAll("input, select, textarea, button").forEach((control) => { control.disabled = true; });
    status.textContent = "Thank you. Your feedback is pending editorial review.";
  } catch { status.textContent = "Feedback could not be saved."; }
}

async function askArchive(question) {
  const result = $("#answer-result");
  result.hidden = false;
  result.innerHTML = '<p class="empty-state">Tracing entities, claims, and evidence…</p>';
  try {
    const language = $("#answer-language").value;
    const languageQuery = language ? `&lang=${encodeURIComponent(language)}` : "";
    renderAnswer(await api(apiPath(`/api/v1/answers?q=${encodeURIComponent(question)}&limit=12${languageQuery}`)));
  } catch {
    result.innerHTML = '<p class="empty-state">The archive could not assemble an answer right now.</p>';
  }
}

const connectionSearchTimers = { from: null, to: null };

function setConnectionEntity(side, entity) {
  $(`#connection-${side}`).value = entity.canonical_name;
  $(`#connection-${side}-id`).value = entity.id;
  $(`#connection-${side}-results`).hidden = true;
}

function startConnectionFrom(entity) {
  setConnectionEntity("from", entity);
  $("#connection-to").value = "";
  $("#connection-to-id").value = "";
  activateView("connection");
  $("#connection-view").scrollIntoView({ behavior: "smooth", block: "start" });
  $("#connection-to").focus();
}

async function searchConnectionEntities(side, query) {
  const container = $(`#connection-${side}-results`);
  if (query.length < 2) { container.hidden = true; return; }
  container.hidden = false;
  container.innerHTML = '<p class="empty-state">Searching…</p>';
  try {
    const data = await api(apiPath(`/api/v1/search?q=${encodeURIComponent(query)}&limit=7`));
    const entities = data.items.filter((item) => item.result_type === "entity");
    container.innerHTML = entities.length ? entities.map((entity) => `
      <button type="button" data-connection-entity="${escapeHtml(entity.id)}" data-connection-name="${escapeHtml(entity.title)}">
        <strong>${escapeHtml(entity.title)}</strong><span>Entity</span>
      </button>`).join("") : '<p class="empty-state">No matching entities.</p>';
    container.querySelectorAll("[data-connection-entity]").forEach((button) => button.addEventListener("click", () => setConnectionEntity(side, {
      id: button.dataset.connectionEntity,
      canonical_name: button.dataset.connectionName,
    })));
  } catch {
    container.innerHTML = '<p class="empty-state">Search is temporarily unavailable.</p>';
  }
}

function connectionQuery() {
  const params = new URLSearchParams({
    from_id: $("#connection-from-id").value,
    to_id: $("#connection-to-id").value,
    max_depth: $("#connection-depth").value,
    limit: "3",
  });
  if ($("#connection-evidence").value) params.set("evidence_level", $("#connection-evidence").value);
  if ($("#connection-verification").value) params.set("verification_status", $("#connection-verification").value);
  return params;
}

function connectionRouteMarkup(path) {
  const parts = [];
  path.nodes.forEach((node, index) => {
    parts.push(`<strong>${escapeHtml(node.canonical_name)}</strong>`);
    const claim = path.claims[index];
    const next = path.nodes[index + 1];
    if (!claim || !next) return;
    const forward = claim.subject.id === node.id && claim.object?.id === next.id;
    const relation = claim.role ? `${readable(claim.predicate)} (${claim.role})` : readable(claim.predicate);
    parts.push(`<span>${forward ? `${escapeHtml(relation)} →` : `← ${escapeHtml(relation)}`}</span>`);
  });
  return parts.join("");
}

function renderConnectionResults(data) {
  const container = $("#connection-results");
  if (!data.paths.length) {
    container.innerHTML = `<p class="empty-state">No reviewed path up to ${data.max_depth} steps connects these entities with the selected filters.</p>`;
    return;
  }
  container.innerHTML = `
    <p class="connection-summary">${data.paths.length} supported ${data.paths.length === 1 ? "path" : "paths"} found between <strong>${escapeHtml(data.source.canonical_name)}</strong> and <strong>${escapeHtml(data.target.canonical_name)}</strong>.</p>
    <div class="connection-paths">${data.paths.map((path, index) => `
      <article class="connection-path">
        <header><strong>Path ${index + 1}</strong><span>${path.length} ${path.length === 1 ? "step" : "steps"} · ${escapeHtml(path.minimum_confidence)} minimum confidence</span></header>
        <div class="connection-route">${connectionRouteMarkup(path)}</div>
        <button type="button" data-show-connection="${index}">Show this path on the graph</button>
      </article>`).join("")}</div>`;
  container.querySelectorAll("[data-show-connection]").forEach((button) => button.addEventListener("click", () => showConnectionPath(data, Number(button.dataset.showConnection))));
}

async function findConnections({ updateHistory = true } = {}) {
  const fromId = $("#connection-from-id").value;
  const toId = $("#connection-to-id").value;
  const container = $("#connection-results");
  if (!fromId || !toId) {
    container.innerHTML = '<p class="empty-state">Select both entities from the search suggestions.</p>';
    return;
  }
  if (fromId === toId) {
    container.innerHTML = '<p class="empty-state">Choose two different entities.</p>';
    return;
  }
  container.innerHTML = '<p class="empty-state">Tracing reviewed paths…</p>';
  const params = connectionQuery();
  try {
    const data = await api(apiPath(`/api/v1/connections?${params}`));
    state.connection = { data, params: new URLSearchParams(params) };
    renderConnectionResults(data);
    if (updateHistory) {
      const shared = new URLSearchParams(params);
      shared.set("view", "connection");
      window.history.replaceState(null, "", `${window.location.pathname}?${shared}`);
    }
  } catch {
    container.innerHTML = '<p class="empty-state">The archive could not trace this connection right now.</p>';
  }
}

async function showConnectionPath(data, pathIndex) {
  const path = data.paths[pathIndex];
  if (!path) return;
  if (state.connection) state.connection.pathIndex = pathIndex;
  state.journey = null;
  state.journeyEntries.clear();
  state.rootEntityId = data.source.id;
  state.activeEntityId = data.source.id;
  state.selectedEdgeId = null;
  state.nodes.clear(); state.edges.clear(); state.positions.clear();
  state.expansionChildren.clear(); state.expandedNodes.clear(); state.history = [];
  state.canvasSize = { width: Math.max(900, path.nodes.length * 210), height: 520 };
  path.nodes.forEach((node, index) => {
    state.nodes.set(node.id, node);
    state.positions.set(node.id, {
      x: 100 + index * ((state.canvasSize.width - 200) / Math.max(path.nodes.length - 1, 1)),
      y: 260 + (index % 2 ? 55 : -55),
    });
  });
  path.claims.forEach((claim) => state.edges.set(claim.id, {
    id: claim.id,
    source: claim.subject.id,
    target: claim.object.id,
    predicate: claim.predicate,
    evidence_level: claim.evidence_level,
    confidence: claim.confidence,
    review_status: claim.review_status,
    verification_status: claim.verification_status,
  }));
  state.initialGraph = graphSnapshot();
  activateView("graph");
  renderGraph();
  await selectNode(data.source.id, false);
  const shared = new URLSearchParams(state.connection?.params || connectionQuery());
  shared.set("view", "graph");
  shared.set("path", String(pathIndex));
  window.history.replaceState(null, "", `${window.location.pathname}?${shared}`);
  $("#graph-view").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function initializeConnectionFromUrl() {
  const fromId = urlState.get("from_id");
  const toId = urlState.get("to_id");
  if (!fromId || !toId) return;
  try {
    const [source, target] = await Promise.all([
      api(apiPath(`/api/v1/entities/${encodeURIComponent(fromId)}`)),
      api(apiPath(`/api/v1/entities/${encodeURIComponent(toId)}`)),
    ]);
    setConnectionEntity("from", source);
    setConnectionEntity("to", target);
    $("#connection-depth").value = urlState.get("max_depth") || "3";
    $("#connection-evidence").value = urlState.get("evidence_level") || "";
    $("#connection-verification").value = urlState.get("verification_status") || "";
    await findConnections({ updateHistory: false });
    const pathIndex = Number(urlState.get("path"));
    if (urlState.get("view") === "graph" && state.connection?.data.paths[pathIndex]) {
      await showConnectionPath(state.connection.data, pathIndex);
    }
  } catch {
    $("#connection-results").innerHTML = '<p class="empty-state">This shared connection could not be restored.</p>';
  }
}

async function loadTimeline() {
  const container = $("#timeline");
  container.innerHTML = '<p class="empty-state">Assembling the relative chronology…</p>';
  try {
    const eraId = $("#timeline-era").value;
    const selected = $("#timeline-era").selectedOptions[0];
    $("#timeline-scope").textContent = eraId ? selected.textContent : "All documented eras";
    const query = eraId ? `?era_id=${encodeURIComponent(eraId)}` : "";
    const data = await api(apiPath(`/api/v1/timeline${query}`));
    if (!data.layers.length) { container.innerHTML = '<p class="empty-state">No reviewed timeline events are available.</p>'; return; }
    const events = Object.fromEntries(data.events.map((event) => [event.id, event]));
    container.innerHTML = data.layers.map((layer, index) => `<section class="timeline-layer"><span class="layer-index">Sequence ${String(index + 1).padStart(2, "0")}</span>${layer.map((eventId) => `<button class="event-card" type="button" data-event-id="${escapeHtml(eventId)}"><strong>${escapeHtml(events[eventId].canonical_name)}</strong><span>${layer.length > 1 ? "Order within this layer unknown" : "Precedence supported"}</span></button>`).join("")}</section>`).join("");
    container.querySelectorAll("[data-event-id]").forEach((button) => button.addEventListener("click", () => { activateView("graph"); loadRoot(button.dataset.eventId); $("#graph-view").scrollIntoView({ behavior: "smooth", block: "start" }); }));
  } catch { container.innerHTML = '<p class="empty-state">The timeline could not be loaded.</p>'; }
}

function activateView(view) {
  document.querySelectorAll(".view-tab").forEach((tab) => tab.classList.toggle("is-active", tab.dataset.view === view));
  $("#graph-view").classList.toggle("is-active", view === "graph");
  $("#connection-view").classList.toggle("is-active", view === "connection");
  $("#timeline-view").classList.toggle("is-active", view === "timeline");
  if (view === "timeline") loadTimeline();
}

$("#search-form").addEventListener("submit", (event) => { event.preventDefault(); const query = $("#search-input").value.trim(); if (query.length >= 2) searchArchive(query); });
$("#question-form").addEventListener("submit", (event) => { event.preventDefault(); const question = $("#question-input").value.trim(); if (question.length >= 3) askArchive(question); });
document.querySelectorAll("[data-question]").forEach((button) => button.addEventListener("click", () => { $("#question-input").value = button.dataset.question; askArchive(button.dataset.question); }));
document.addEventListener("click", (event) => { if (!event.target.closest(".hero")) $("#search-results").hidden = true; });
document.querySelectorAll(".view-tab").forEach((tab) => tab.addEventListener("click", () => activateView(tab.dataset.view)));
$("#expand-node").addEventListener("click", () => expandNode());
$("#collapse-node").addEventListener("click", collapseSelected);
$("#focus-node").addEventListener("click", () => {
  if (state.activeEntityId) loadRoot(state.activeEntityId);
});
$("#hide-node").addEventListener("click", hideSelected);
$("#arrange-graph").addEventListener("click", arrangeGraph);
function setZoom(value) {
  state.zoom = Math.max(0.5, Math.min(2, value));
  $("#zoom-reset").textContent = `${Math.round(state.zoom * 100)}%`;
  renderGraph();
}
$("#zoom-in").addEventListener("click", () => setZoom(state.zoom + 0.15));
$("#zoom-out").addEventListener("click", () => setZoom(state.zoom - 0.15));
$("#zoom-reset").addEventListener("click", () => setZoom(1));
$("#undo-graph").addEventListener("click", undoGraph);
$("#reset-graph").addEventListener("click", resetGraph);
$("#kind-filter").addEventListener("change", (event) => { state.kindFilter = event.target.value; renderGraph(); });
$("#evidence-filter").addEventListener("change", (event) => { state.evidenceFilter = event.target.value; renderGraph(); });
$("#timeline-era").addEventListener("change", loadTimeline);
for (const side of ["from", "to"]) {
  $(`#connection-${side}`).addEventListener("input", (event) => {
    $(`#connection-${side}-id`).value = "";
    clearTimeout(connectionSearchTimers[side]);
    connectionSearchTimers[side] = setTimeout(() => searchConnectionEntities(side, event.target.value.trim()), 220);
  });
}
$("#connection-form").addEventListener("submit", (event) => {
  event.preventDefault();
  findConnections();
});
$("#spoiler-level").value = state.spoilerLevel;
$("#spoiler-level").addEventListener("change", async (event) => {
  state.spoilerLevel = event.target.value;
  if (state.journey && { minimal: 0, base_game: 1, full: 2 }[state.journey.spoiler_level] > { minimal: 0, base_game: 1, full: 2 }[state.spoilerLevel]) {
    state.journey = null;
    state.journeyEntries.clear();
  }
  await loadDiscoveryCollections();
  updateUrl();
});
const dialog = $("#about-dialog");
$("#about-button").addEventListener("click", () => dialog.showModal());
$("#dialog-close").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });

async function initializeApp() {
  checkStatus();
  const expandedFromUrl = (urlState.get("expanded") || "").split(",").filter(Boolean).slice(0, 20);
  loadDiscoveryCollections();
  const journeyFromUrl = urlState.get("journey");
  if (journeyFromUrl) await loadJourney(journeyFromUrl);
  else {
    await loadRoot(state.rootEntityId, expandedFromUrl);
    if (urlState.get("view") === "connection" || urlState.get("from_id")) {
      activateView("connection");
      await initializeConnectionFromUrl();
    }
  }
  const sharedQuestion = urlState.get("question");
  if (sharedQuestion && sharedQuestion.length >= 3) {
    $("#question-input").value = sharedQuestion;
    await askArchive(sharedQuestion);
  }
}

initializeApp();
