const tokenInput = document.querySelector("#editorial-token");
const workspace = document.querySelector("#editorial-workspace");
const queue = document.querySelector("#editorial-queue");
let editorialToken = sessionStorage.getItem("editorialToken") || "";
let currentKind = "priority";
tokenInput.value = editorialToken;

function escaped(value = "") { const node = document.createElement("span"); node.textContent = String(value); return node.innerHTML; }
async function editorialApi(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", "X-Editorial-Token": editorialToken, ...(options.headers || {}) } });
  if (!response.ok) throw new Error((await response.json()).detail || `Request failed: ${response.status}`);
  return response.json();
}
async function loadDashboard() {
  const [data, readiness] = await Promise.all([editorialApi("/api/v1/editorial/dashboard"), editorialApi("/api/v1/editorial/readiness")]);
  document.querySelector("#editorial-metrics").innerHTML = Object.entries(data).map(([key, value]) => `<article><strong>${value}</strong><span>${escaped(key.replaceAll("_", " "))}</span></article>`).join("");
  document.querySelector("#editorial-readiness").innerHTML = `<h2>Review readiness</h2><p>${readiness.evidence_ready} evidence records meet structural checks · ${readiness.claims_ready} claims ready after evidence review · ${readiness.claims_blocked} claims blocked</p><ol>${readiness.policy.map((item) => `<li>${escaped(item)}</li>`).join("")}</ol>`;
}
async function loadQueue(kind = "priority", statusValue = "draft") {
  currentKind = kind;
  queue.innerHTML = '<p class="empty-state">Loading review queue…</p>';
  const priority = kind === "priority";
  const effectiveKind = priority ? "evidence" : kind;
  const items = await editorialApi(priority ? "/api/v1/editorial/priority-evidence?limit=100" : `/api/v1/editorial/queue?kind=${kind}&status_value=${statusValue}&limit=100`);
  document.querySelector("#editorial-batch").hidden = !items.length;
  queue.innerHTML = items.length ? items.map((item) => `<article class="review-card" data-id="${escaped(item.id)}" data-kind="${effectiveKind}"><header><label><input class="review-select" type="checkbox" aria-label="Select ${escaped(item.id)}"><strong>${escaped(item.id)}</strong></label><span>${escaped(item.review_status || item.moderation_status)}</span></header>${priority ? `<div class="review-impact"><strong>${item.unlock_count} claims unlocked now</strong><span>${item.impact_count} dependent claims · ${escaped((item.entity_names || []).join(" · "))}</span></div>` : ""}<pre>${escaped(JSON.stringify(item, null, 2))}</pre>${["claim", "evidence"].includes(effectiveKind) ? '<label>Verification level<select class="verification-level"><option value="community_verified">Community verified</option><option value="official_verified">Official verified</option><option value="game_verified">Game verified (highest)</option><option value="unverified">Unverified</option></select></label><input class="verification-url" type="url" placeholder="Verification source URL (required for community)">' : ""}<textarea maxlength="2000" placeholder="Editorial notes"></textarea><div><button data-decision="${effectiveKind === "feedback" ? "approved" : "reviewed"}">Approve</button><button data-decision="rejected">Reject</button>${effectiveKind === "claim" ? '<button data-decision="disputed">Disputed</button>' : ""}</div><p role="status"></p></article>`).join("") : '<p class="empty-state">No items in this queue.</p>';
  queue.querySelectorAll("[data-decision]").forEach((button) => button.addEventListener("click", () => reviewItem(button)));
}
async function reviewItem(button) {
  const card = button.closest(".review-card"); const status = card.querySelector('[role="status"]'); status.textContent = "Saving…";
  try { await editorialApi(`/api/v1/editorial/${card.dataset.kind}/${encodeURIComponent(card.dataset.id)}`, { method: "PATCH", body: JSON.stringify({ decision: button.dataset.decision, notes: card.querySelector("textarea").value.trim() || null, verification_status: card.querySelector(".verification-level")?.value || null, verification_url: card.querySelector(".verification-url")?.value.trim() || null }) }); card.remove(); await loadDashboard(); }
  catch (error) { status.textContent = error.message; }
}
document.querySelector("#editorial-login").addEventListener("submit", async (event) => { event.preventDefault(); editorialToken = tokenInput.value; sessionStorage.setItem("editorialToken", editorialToken); try { await loadDashboard(); workspace.hidden = false; await loadQueue(); } catch (error) { alert(error.message); } });
document.querySelectorAll("[data-kind]").forEach((button) => button.addEventListener("click", () => loadQueue(button.dataset.kind, button.dataset.status || "draft")));
document.querySelector("#select-all").addEventListener("click", () => {
  queue.querySelectorAll(".review-select").forEach((checkbox) => { checkbox.checked = true; });
});
document.querySelector("#approve-selected").addEventListener("click", async () => {
  const cards = [...queue.querySelectorAll(".review-card")].filter((card) => card.querySelector(".review-select").checked);
  if (!cards.length) return;
  const status = document.querySelector("#batch-status");
  status.textContent = "Saving selection…";
  try {
    const effectiveKind = currentKind === "priority" ? "evidence" : currentKind;
    const verificationStatus = ["claim", "evidence"].includes(effectiveKind) ? document.querySelector("#batch-verification").value : null;
    const verificationUrl = document.querySelector("#batch-verification-url").value.trim() || null;
    const result = await editorialApi(`/api/v1/editorial/${effectiveKind}/batch`, {
      method: "POST",
      body: JSON.stringify({ item_ids: cards.map((card) => card.dataset.id), decision: effectiveKind === "feedback" ? "approved" : "reviewed", notes: "Batch reviewed in editorial console", verification_status: verificationStatus, verification_url: verificationUrl }),
    });
    const reviewedIds = new Set(result.reviewed.map((item) => item.id));
    cards.filter((card) => reviewedIds.has(card.dataset.id)).forEach((card) => card.remove());
    status.textContent = `${result.reviewed.length} reviewed · ${result.errors.length} blocked`;
    await loadDashboard();
  } catch (error) { status.textContent = error.message; }
});
