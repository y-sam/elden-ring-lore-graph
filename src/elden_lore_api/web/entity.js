const params = new URLSearchParams(window.location.search);
const entityId = params.get("id");
const includeDrafts = ["localhost", "127.0.0.1"].includes(window.location.hostname);
const profile = document.querySelector("#entity-profile");

function escaped(value = "") {
  const node = document.createElement("span");
  node.textContent = String(value);
  return node.innerHTML;
}

function readable(value = "") {
  return value.toLowerCase().replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function api(path) {
  const separator = path.includes("?") ? "&" : "?";
  const response = await fetch(`${path}${separator}include_drafts=${includeDrafts}`);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

function evidenceMarkup(evidence) {
  return evidence.map((item) => `<details class="evidence"><summary>${escaped(item.locator)}</summary><p>${escaped(item.summary_en)}</p><cite>${escaped(item.source_title)} · ${escaped(item.authority_tier)} · ${escaped(readable(item.verification_status))}</cite></details>`).join("");
}

function claimContext(claim) {
  return [
    claim.role ? `Role: ${claim.role}` : "",
    claim.temporal_scope ? `Time: ${readable(claim.temporal_scope)}` : "",
    claim.qualifier || "",
  ].filter(Boolean).join(" · ");
}

function claimMarkup(claim) {
  const counterpart = claim.direction === "outgoing" ? claim.object : claim.subject;
  return `<article class="profile-claim"><header><span class="predicate">${escaped(readable(claim.predicate))}</span><span class="chip">${escaped(claim.confidence)} confidence</span></header><p><span>${claim.direction === "incoming" ? "From" : "To"}</span> <a href="/entity.html?id=${encodeURIComponent(counterpart.id)}">${escaped(counterpart.canonical_name)}</a></p>${claimContext(claim) ? `<p class="claim-context">${escaped(claimContext(claim))}</p>` : ""}<div class="claim-meta"><span class="chip">${escaped(readable(claim.evidence_level))}</span><span class="chip">${escaped(claim.review_status)}</span><span class="chip">${escaped(readable(claim.verification_status))}</span><span class="chip">${escaped(claim.continuity)}</span></div>${evidenceMarkup(claim.evidence)}</article>`;
}

async function loadProfile() {
  if (!entityId) { profile.innerHTML = '<p class="empty-state">No entity was selected.</p>'; return; }
  document.querySelector("#open-graph").href = `/?entity=${encodeURIComponent(entityId)}`;
  try {
    const entity = await api(`/api/v1/entities/${encodeURIComponent(entityId)}`);
    const answer = await api(`/api/v1/answers?q=${encodeURIComponent(`Who is ${entity.canonical_name}?`)}&lang=en&limit=8`);
    document.title = `${entity.canonical_name} · The Lands Between`;
    const related = new Map();
    entity.claims.forEach((claim) => {
      const counterpart = claim.direction === "outgoing" ? claim.object : claim.subject;
      if (counterpart) related.set(counterpart.id, counterpart);
    });
    profile.innerHTML = `<header class="profile-hero"><p class="eyebrow">${escaped(entity.kind)} · ${escaped(entity.continuity)}</p><h1>${escaped(entity.canonical_name)}</h1><p class="entity-id">${escaped(entity.id)}</p><p class="profile-summary">${escaped(answer.answer)}</p><div class="profile-status"><span class="answer-status ${escaped(answer.status)}">${escaped(answer.status)}</span><span>${answer.citations.length} citations</span><span>${entity.claims.length} relationships</span></div></header><section class="profile-section"><h2>Evidence-backed relationships</h2><div class="profile-claims">${entity.claims.length ? entity.claims.map(claimMarkup).join("") : '<p class="empty-state">No reviewed relationships are available.</p>'}</div></section><aside class="profile-section"><h2>Related entities</h2><div class="answer-entities">${[...related.values()].map((item) => `<a href="/entity.html?id=${encodeURIComponent(item.id)}">${escaped(item.canonical_name)}</a>`).join("") || "None yet"}</div></aside><section class="profile-section"><form class="feedback-form" id="profile-feedback"><h2>Help the editorial team assess this profile</h2><div class="feedback-ratings"><label><input type="radio" name="rating" value="helpful" required> Helpful</label><label><input type="radio" name="rating" value="mixed"> Mixed</label><label><input type="radio" name="rating" value="not_helpful"> Not helpful</label></div><select name="reason"><option value="">Reason (optional)</option><option value="accurate">Accurate</option><option value="missing_context">Missing context</option><option value="wrong_fact">Wrong fact</option><option value="weak_evidence">Weak evidence</option><option value="other">Other</option></select><textarea name="comment" maxlength="1000" rows="3" placeholder="Editorial comment (optional)"></textarea><button type="submit">Send profile feedback</button><span class="feedback-status" role="status"></span></form></section>`;
    document.querySelector("#profile-feedback").addEventListener("submit", (event) => submitProfileFeedback(event, answer));
  } catch { profile.innerHTML = '<p class="empty-state">This entity profile could not be loaded.</p>'; }
}

async function submitProfileFeedback(event, answer) {
  event.preventDefault();
  const form = event.currentTarget;
  const values = new FormData(form);
  const status = form.querySelector(".feedback-status");
  status.textContent = "Sending…";
  const claims = [...answer.explicit_claims, ...answer.inferred_claims, ...answer.supporting_claims];
  try {
    const response = await fetch("/api/v1/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ answer_id: answer.answer_id, question: answer.question, language: "en", rating: values.get("rating"), reason: values.get("reason") || null, comment: values.get("comment")?.trim() || null, claim_ids: claims.map((claim) => claim.id) }),
    });
    if (!response.ok) throw new Error("feedback failed");
    form.querySelectorAll("input, select, textarea, button").forEach((control) => { control.disabled = true; });
    status.textContent = "Thank you. Your feedback is pending editorial review.";
  } catch { status.textContent = "Feedback could not be saved."; }
}

loadProfile();
