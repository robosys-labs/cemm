"use strict";

const token = new URLSearchParams(location.hash.slice(1)).get("token");
const workspace = document.getElementById("workspace");
const statusHeader = document.getElementById("status-header");
const impactDialog = document.getElementById("impact-dialog");
const impactContent = document.getElementById("impact-content");
const confirmImpact = document.getElementById("confirm-impact");
const toast = document.getElementById("toast");
const navigation = Array.from(document.querySelectorAll("[data-section]"));
const modeNavigation = Array.from(document.querySelectorAll("[data-mode]"));
const guidedProgress = document.getElementById("guided-progress");
const advancedNavigation = document.getElementById("advanced-nav");

const view = {
  bootstrap: null,
  guidedBootstrap: null,
  mode: "guided",
  guidedStarted: false,
  guidedItem: null,
  guidedAfterRef: null,
  guidedPassStartRef: null,
  section: "dashboard",
  filter: "unresolved",
  query: "",
  offset: 0,
  limit: 25,
  pendingPreview: null,
  busy: false,
};

let toastTimer = null;

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function api(path, {method = "GET", body = null} = {}) {
  const headers = {"X-CEMM-Review-Token": token || ""};
  if (body !== null) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(path, {
    method,
    headers,
    body: body === null ? null : JSON.stringify(body),
  });
  const envelope = await response.json();
  if (!response.ok || envelope.ok !== true) {
    const detail = typeof envelope.error === "string"
      ? envelope.error
      : envelope.error && envelope.error.message;
    throw new ApiError(detail || `Request failed: ${response.status}`, response.status);
  }
  return envelope;
}

function node(tag, className = "", text = null) {
  const result = document.createElement(tag);
  if (className) result.className = className;
  if (text !== null) result.textContent = String(text);
  return result;
}

function append(parent, ...children) {
  for (const child of children) parent.append(child);
  return parent;
}

function badge(text, state) {
  return node("span", `badge ${state}`, text);
}

function titleBlock(eyebrow, title, description) {
  const wrapper = node("div", "page-heading");
  const copy = node("div");
  append(copy, node("p", "eyebrow", eyebrow), node("h2", "", title));
  if (description) copy.append(node("p", "", description));
  wrapper.append(copy);
  return wrapper;
}

function metric(label, value) {
  const item = node("div", "metric");
  append(item, node("span", "", label), node("strong", "", value));
  return item;
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.add("visible");
  if (toastTimer !== null) window.clearTimeout(toastTimer);
  toastTimer = window.setTimeout(() => toast.classList.remove("visible"), 4500);
}

function setBusy(busy) {
  view.busy = busy;
  document.body.classList.toggle("loading", busy);
  for (const control of document.querySelectorAll("button, input, select")) {
    if (busy) {
      control.dataset.busyPreviousDisabled = String(control.disabled);
      control.disabled = true;
    } else if (Object.hasOwn(control.dataset, "busyPreviousDisabled")) {
      control.disabled = control.dataset.busyPreviousDisabled === "true";
      delete control.dataset.busyPreviousDisabled;
    }
  }
}

function currentRevisionBody(extra = {}) {
  return {state_revision: view.bootstrap.state_revision, ...extra};
}

async function recover(error) {
  view.pendingPreview = null;
  if (impactDialog.open) impactDialog.close("cancel");
  if (error instanceof ApiError && error.status === 409) {
    showToast("Review state changed; reloaded current state.");
    await refresh();
    if (view.mode === "guided" && view.guidedStarted) {
      await loadGuidedNext(null);
    }
    return;
  }
  showToast(`${error.message}. Review the action and try again.`);
}

function renderStatusHeader() {
  statusHeader.replaceChildren();
  const brand = node("div", "brand-block");
  append(
    brand,
    node("p", "eyebrow", "R4.1 · Local accountable review"),
    node("h1", "", "CEMM semantic supervision")
  );
  const statuses = node("div", "status-cluster");
  statuses.append(
    badge(
      view.bootstrap.review_complete ? "Review complete" : "Review unresolved",
      view.bootstrap.review_complete ? "complete" : "unresolved"
    ),
    badge(
      view.bootstrap.authoring_ready ? "Authoring ready" : "Authoring blocked",
      view.bootstrap.authoring_ready ? "complete" : "rejected"
    ),
    badge(`Revision ${view.bootstrap.state_revision}`, "unresolved")
  );
  append(statusHeader, brand, statuses);
}

function renderDashboard() {
  workspace.replaceChildren();
  workspace.append(titleBlock(
    "Review control",
    "Accountable review dashboard",
    "Inspect authenticated evidence, record reviewer-owned decisions, and export only after exact validation."
  ));
  const layout = node("div", "dashboard-grid");
  const primary = node("section", "card-grid");
  const metrics = node("div", "metric-grid");
  const inventory = view.bootstrap.inventory;
  append(
    metrics,
    metric("Structural", inventory.structural),
    metric("Purpose", inventory.purpose),
    metric("Recipe families", inventory.recipe_family),
    metric("Designations", inventory.designation)
  );
  primary.append(metrics);

  const progress = node("section", "panel");
  progress.append(node("h3", "", "Current review state"));
  const counts = node("div", "metric-grid");
  for (const [label, key] of [
    ["Structural unresolved", "unresolved_structural"],
    ["Purpose unresolved", "unresolved_purpose"],
    ["Recipes unresolved", "unresolved_recipe"],
    ["Designations unresolved", "unresolved_designation"],
  ]) {
    counts.append(metric(label, view.bootstrap.review_counts[key]));
  }
  progress.append(counts);
  if (view.bootstrap.blocking_rejection_refs.length) {
    const rejection = node("div", "danger-note");
    rejection.append(node("strong", "", "Blocking reviewed rejections"));
    rejection.append(referenceList(view.bootstrap.blocking_rejection_refs));
    progress.append(rejection);
  }
  primary.append(progress);

  const risk = node("section", "panel");
  risk.append(node("h3", "", "Designation exception inventory"));
  const riskMetrics = node("div", "metric-grid");
  for (const [label, key] of [
    ["Intersecting cases", "intersecting_case"],
    ["Overlap pairs", "overlap_pair"],
    ["Multi-unit cases", "multi_unit_case"],
    ["Exact-empty cases", "exact_empty"],
  ]) {
    riskMetrics.append(metric(label, view.bootstrap.designation_risk_counts[key]));
  }
  risk.append(riskMetrics);
  primary.append(risk);

  const reviewerPanel = node("aside", "panel sticky-panel");
  reviewerPanel.append(node("h3", "", "Accountable reviewers"));
  const form = node("form", "field");
  const label = node("label", "", "Canonical reviewer refs");
  label.htmlFor = "reviewer-refs";
  const input = node("input");
  input.id = "reviewer-refs";
  input.type = "text";
  input.autocomplete = "off";
  input.value = view.bootstrap.reviewer_refs.join(", ");
  input.setAttribute("aria-describedby", "reviewer-help");
  const help = node(
    "p",
    "helper",
    "Comma-separated typed refs, sorted canonically. Saving is required before any decision preview."
  );
  help.id = "reviewer-help";
  const save = node("button", "button primary", "Save reviewers");
  save.type = "submit";
  append(form, label, input, help, save);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const refs = input.value
      .split(",")
      .map((value) => value.trim())
      .filter(Boolean)
      .sort();
    await runMutation(async () => {
      await api("/api/reviewer", {
        method: "POST",
        body: currentRevisionBody({reviewer_refs: Array.from(new Set(refs))}),
      });
      showToast("Reviewer identity saved to working state.");
      await refresh();
    });
  });
  reviewerPanel.append(form);
  if (view.bootstrap.audit_warning) {
    reviewerPanel.append(node("p", "warning", view.bootstrap.audit_warning));
  }
  const identity = node("details");
  identity.append(node("summary", "", "Authenticated review identity"));
  const identityPre = node("pre");
  identityPre.textContent = JSON.stringify({
    selection_template_ref: view.bootstrap.selection_template_ref,
    draft_input_set_ref: view.bootstrap.draft_input_set_ref,
  }, null, 2);
  identity.append(identityPre);
  reviewerPanel.append(identity);

  const shutdown = node("button", "button danger", "Stop local review server");
  shutdown.type = "button";
  shutdown.addEventListener("click", async () => {
    if (!window.confirm("Stop this local review server? Saved working state will remain.")) return;
    await runMutation(async () => {
      await api("/api/shutdown", {method: "POST", body: currentRevisionBody()});
      showToast("Local review server stopped. You may close this tab.");
    });
  });
  reviewerPanel.append(node("hr"), shutdown);
  append(layout, primary, reviewerPanel);
  workspace.append(layout);
}

function renderGuidedStart() {
  workspace.replaceChildren();
  guidedProgress.textContent = "Ready to begin · decisions are saved only after confirmation";
  const shell = node("section", "guided-shell panel");
  append(
    shell,
    node("p", "eyebrow", "R4.1 accountable review"),
    node("h2", "", "Verify one semantic decision at a time"),
    node(
      "p",
      "guided-lead",
      "You are verifying the bounded semantic supervision CEMM will use for R4.1. The system will explain each decision and show its evidence. It will not choose meaning for you."
    )
  );
  const hasProgress = view.bootstrap.reviewer_refs.length > 0;
  const actions = node("div", "button-row guided-actions");
  const start = node(
    "button",
    "button primary",
    hasProgress ? "Resume guided review" : "Start guided review"
  );
  start.type = "button";
  start.addEventListener("click", () => runMutation(async () => {
    view.guidedStarted = true;
    await loadGuidedNext(null);
  }));
  const advanced = node("button", "button secondary", "Open Advanced Explorer");
  advanced.type = "button";
  advanced.addEventListener("click", () => switchMode("advanced"));
  append(actions, start, advanced);
  shell.append(actions);
  const explanation = node("details", "technical-evidence");
  explanation.append(node("summary", "", "What will I be asked to do?"));
  explanation.append(node(
    "p",
    "",
    "Read the displayed source and evidence, answer one neutral question, review the impact, then explicitly confirm or skip it for later."
  ));
  shell.append(explanation);
  workspace.append(shell);
}

function technicalEvidence(value) {
  const details = node("details", "technical-evidence");
  details.append(node("summary", "", "Technical evidence"));
  const pre = node("pre");
  pre.textContent = JSON.stringify(value, null, 2);
  details.append(pre);
  return details;
}

function renderGuidedIdentity(item) {
  workspace.replaceChildren();
  const shell = node("section", "guided-shell panel");
  append(shell, node("p", "eyebrow", "Step 1 · Reviewer identity"), node("h2", "", "Identify the accountable reviewer"), node("p", "guided-lead", item.instruction));
  const form = node("form", "field guided-identity");
  const label = node("label", "", "Canonical reviewer ref");
  label.htmlFor = "guided-reviewer-ref";
  const input = node("input");
  input.id = "guided-reviewer-ref";
  input.type = "text";
  input.placeholder = "reviewer:your-name";
  input.autocomplete = "off";
  const help = node("p", "helper", "Use a stable typed identity such as reviewer:son. Nothing is confirmed by entering it.");
  const save = node("button", "button primary", "Save reviewer and continue");
  save.type = "submit";
  append(form, label, input, help, save);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const ref = input.value.trim();
    runMutation(async () => {
      await api("/api/reviewer", {method: "POST", body: currentRevisionBody({reviewer_refs: ref ? [ref] : []})});
      await refresh();
      await loadGuidedNext(null);
    });
  });
  shell.append(form);
  workspace.append(shell);
}

function renderGuidedItem() {
  const item = view.guidedItem;
  if (!item) return renderGuidedStart();
  if (item.phase === "identity") {
    guidedProgress.textContent = "Reviewer identity · required before decisions";
    renderGuidedIdentity(item);
    return;
  }
  if (item.phase === "export") {
    guidedProgress.textContent = "Final step · validate and export";
    renderGuidedCompletion(item);
    return;
  }
  workspace.replaceChildren();
  guidedProgress.textContent = `Current phase · ${item.phase}`;
  const shell = node("article", "guided-shell guided-step panel");
  append(shell, node("p", "eyebrow", `${item.phase} review`), node("h2", "", "Review this one decision"), node("p", "guided-lead", item.instruction));
  const source = node("section", "guided-evidence-block");
  append(source, node("h3", "", "Source to verify"), node("blockquote", "", item.source_summary));
  const proposal = node("section", "guided-evidence-block");
  append(proposal, node("h3", "", "What CEMM proposes"), node("p", "", item.proposal_summary));
  append(shell, source, proposal);
  if (item.cohort) {
    const cohort = node("section", "guided-evidence-block");
    append(cohort, node("h3", "", `Exact cohort · ${item.cohort.member_count} cases`), node("p", "", `Examples: ${item.cohort.representative_examples.join(", ")}`));
    shell.append(cohort);
  }
  const question = node("section", "guided-question");
  append(question, node("p", "eyebrow", "Your decision"), node("h3", "", item.reviewer_question));
  const choices = node("div", "choice-grid");
  for (const choice of item.choices) {
    const button = node("button", "choice-card");
    button.type = "button";
    append(button, node("strong", "", choice.label), node("span", "", choice.explanation), node("small", choice.blocks_authoring ? "blocking-copy" : "", choice.consequence));
    button.addEventListener("click", () => previewGuidedChoice(choice.choice_ref));
    choices.append(button);
  }
  question.append(choices);
  const skip = node("button", "button secondary", "Skip for now");
  skip.type = "button";
  skip.addEventListener("click", skipGuidedItem);
  append(shell, question, skip, technicalEvidence(item.technical_evidence));
  workspace.append(shell);
}

function renderGuidedCompletion(item) {
  workspace.replaceChildren();
  const shell = node("section", "guided-shell panel");
  let title = "Review incomplete";
  let copy = "Applicable decisions remain unresolved. Return to guided review and resolve or revisit them before export.";
  let stateClass = "warning";
  if (item.review_complete && !item.authoring_ready) {
    title = "Review recorded; authoring blocked";
    copy = "The accountable review is complete, but rejection decisions require repair before Task 10B can continue.";
    stateClass = "danger-note";
  } else if (item.review_complete && item.authoring_ready) {
    title = "Review complete and authoring ready";
    copy = "Every applicable decision is complete and no blocking rejection remains. Validate and export the exact selection.";
    stateClass = "success-note";
  }
  append(shell, node("p", "eyebrow", "R4.1 review outcome"), node("h2", "", title), node("p", stateClass, copy));
  if (item.review_complete) {
    const receipt = node("div");
    const exportButton = node("button", "button primary", "Validate and export exact selection");
    exportButton.type = "button";
    exportButton.addEventListener("click", () => runMutation(async () => {
      const envelope = await api("/api/export", {method: "POST", body: currentRevisionBody()});
      const pre = node("pre");
      pre.textContent = JSON.stringify(envelope.result, null, 2);
      receipt.replaceChildren(node("h3", "", "Validated export receipt"), pre);
      showToast("Canonical reviewed selection exported.");
    }));
    append(shell, exportButton, receipt);
  }
  if (item.blocking_rejection_refs.length) {
    shell.append(technicalEvidence({blocking_rejection_refs: item.blocking_rejection_refs}));
  }
  workspace.append(shell);
}

async function previewGuidedChoice(choiceRef) {
  await runMutation(async () => {
    const envelope = await api("/api/guided/preview", {method: "POST", body: currentRevisionBody({item_ref: view.guidedItem.item_ref, choice_ref: choiceRef})});
    showPreview({...envelope.result, guided: true});
  });
}

async function skipGuidedItem() {
  if (!view.guidedItem) return;
  const current = view.guidedItem.item_ref;
  if (view.guidedPassStartRef === null) view.guidedPassStartRef = current;
  await runMutation(async () => {
    const params = new URLSearchParams({after: current});
    const envelope = await api(`/api/guided/next?${params.toString()}`);
    if (envelope.result.item_ref === view.guidedPassStartRef) return renderSkippedPassComplete();
    view.guidedItem = envelope.result;
    renderCurrentSection();
  });
}

function renderSkippedPassComplete() {
  workspace.replaceChildren();
  const shell = node("section", "guided-shell panel");
  append(shell, node("p", "eyebrow", "No decisions were recorded"), node("h2", "", "You have reached every unresolved decision"), node("p", "guided-lead", "Skipped decisions remain unresolved. Revisit them when you have enough evidence; the review cannot complete by skipping them."));
  const revisit = node("button", "button primary", "Revisit skipped decisions");
  revisit.type = "button";
  revisit.addEventListener("click", () => {
    view.guidedPassStartRef = null;
    loadGuidedNext(null);
  });
  shell.append(revisit);
  workspace.append(shell);
}

async function loadGuidedNext(afterItemRef) {
  const params = new URLSearchParams({after: afterItemRef || ""});
  const envelope = await api(`/api/guided/next?${params.toString()}`);
  view.guidedItem = envelope.result;
  view.guidedAfterRef = afterItemRef;
  renderCurrentSection();
}

function switchMode(mode) {
  view.mode = mode;
  if (mode === "advanced") view.section = "dashboard";
  renderCurrentSection();
}

function renderToolbar() {
  const form = node("form", "toolbar");
  const searchField = node("div", "field grow");
  const searchLabel = node("label", "", "Search exact evidence");
  searchLabel.htmlFor = "review-search";
  const search = node("input");
  search.id = "review-search";
  search.type = "search";
  search.value = view.query;
  append(searchField, searchLabel, search);

  const filterField = node("div", "field");
  const filterLabel = node("label", "", "Decision state");
  filterLabel.htmlFor = "review-filter";
  const filter = node("select");
  filter.id = "review-filter";
  for (const value of ["unresolved", "all", "completed", "rejected", "exception"]) {
    const option = node("option", "", value.replace("_", " "));
    option.value = value;
    option.selected = value === view.filter;
    filter.append(option);
  }
  append(filterField, filterLabel, filter);
  const submit = node("button", "button primary", "Apply filters");
  submit.type = "submit";
  append(form, searchField, filterField, submit);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    view.query = search.value.trim();
    view.filter = filter.value;
    view.offset = 0;
    renderCurrentSection();
  });
  return form;
}

function evidenceDetails(item) {
  const details = node("details");
  details.append(node("summary", "", "Inspect exact evidence and refs"));
  const pre = node("pre");
  pre.textContent = JSON.stringify({
    row_ref: item.row_ref,
    subject_ref: item.subject_ref,
    display: item.display,
  }, null, 2);
  details.append(pre);
  return details;
}

function baseCard(item, title) {
  const card = node("article", "card");
  card.dataset.state = item.state;
  const header = node("div", "card-header");
  const copy = node("div");
  append(copy, node("h3", "", title), node("span", "ref", item.subject_ref));
  append(header, copy, badge(item.state, item.state));
  card.append(header);
  const current = node("div", "current-value");
  current.append(node("strong", "", "Current decision"));
  const currentPre = node("pre");
  currentPre.textContent = JSON.stringify(item.current_value, null, 2);
  current.append(currentPre);
  append(card, current, evidenceDetails(item));
  return card;
}

function actionButton(label, action, danger = false) {
  const button = node("button", `button${danger ? " danger" : ""}`, label.replaceAll("_", " "));
  button.type = "button";
  button.addEventListener("click", () => previewAction(action));
  return button;
}

function renderStructuralCard(item) {
  const card = baseCard(item, item.row_kind.replaceAll("_", " "));
  const actions = node("div", "button-row");
  for (const option of item.options.filter((value) => value.selectable === true)) {
    actions.append(actionButton(
      option.label,
      {
        action_kind: "structural",
        target_refs: [item.row_ref],
        selected_value: option.option_ref,
      },
      option.label.startsWith("reject")
    ));
  }
  card.append(actions);
  return card;
}

function renderPurposeCard(item) {
  const card = baseCard(item, item.row_kind.replaceAll("_", " "));
  const actions = node("div", "button-row");
  for (const option of item.options.filter((value) => value.selectable === true)) {
    actions.append(actionButton(
      option.label,
      {
        action_kind: "purpose",
        target_refs: [item.row_ref],
        selected_value: option.label,
      },
      option.label.startsWith("reject")
    ));
  }
  card.append(actions);
  return card;
}

function renderRecipeCard(item) {
  const card = baseCard(item, `Recipe family · ${item.display.target_kind}`);
  const actions = node("div", "button-row");
  for (const purpose of item.display.eligible_purposes) {
    for (const decision of item.options) {
      actions.append(actionButton(
        `${decision} ${purpose}`,
        {
          action_kind: "recipe",
          target_refs: [item.row_ref],
          selected_value: {
            purpose,
            decision,
            reviewed_parameters: {review_basis: "accountable_ui_exact_family"},
          },
        },
        decision === "reject"
      ));
    }
  }
  card.append(actions);
  return card;
}

function renderDesignationCard(item) {
  const card = baseCard(item, item.display.surface || item.row_ref);
  const badges = node("div", "badge-row");
  if (item.display.exceptional) {
    badges.append(badge("Individual review required", "exception"));
  } else {
    badges.append(badge("Routine cohort", "complete"));
  }
  card.append(badges);
  const actions = node("div", "button-row");
  for (const decision of item.options) {
    const action = item.display.exceptional
      ? {
          action_kind: "designation_cases",
          target_refs: [item.row_ref],
          selected_value: {decision, individual: true},
        }
      : {
          action_kind: "designation_cohort",
          target_refs: [item.display.routine_cohort_ref],
          selected_value: decision,
        };
    actions.append(actionButton(decision, action, decision === "reject"));
  }
  card.append(actions);
  return card;
}

function referenceList(refs) {
  const list = node("ul");
  for (const ref of refs) list.append(node("li", "ref", ref));
  return list;
}

async function renderItems() {
  workspace.replaceChildren();
  workspace.append(titleBlock(
    "Evidence review",
    view.section === "recipe" ? "Proposal recipe families" : `${view.section[0].toUpperCase()}${view.section.slice(1)} decisions`,
    "Every option below is a server-created projection of the authenticated review bundle."
  ));
  workspace.append(renderToolbar());
  const params = new URLSearchParams({
    section: view.section,
    filter: view.filter,
    query: view.query,
    offset: String(view.offset),
    limit: String(view.limit),
  });
  const envelope = await api(`/api/items?${params.toString()}`);
  const page = envelope.result;
  const layout = node("div", "review-layout");
  const cards = node("section", "card-grid");
  const renderer = {
    structural: renderStructuralCard,
    purpose: renderPurposeCard,
    recipe: renderRecipeCard,
    designation: renderDesignationCard,
  }[view.section];
  if (!page.items.length) {
    cards.append(node("div", "empty-state", "No review items match the current filter."));
  } else {
    for (const item of page.items) cards.append(renderer(item));
  }
  const summary = node("aside", "panel sticky-panel");
  append(
    summary,
    node("h3", "", "Current result set"),
    metric("Matching items", page.total),
    node("p", "muted", `Showing ${page.offset + 1}–${Math.min(page.offset + page.items.length, page.total)}.`)
  );
  append(layout, cards, summary);
  workspace.append(layout);

  const pagination = node("div", "pagination");
  const previous = node("button", "button secondary", "Previous page");
  previous.type = "button";
  previous.disabled = page.offset === 0;
  previous.addEventListener("click", () => {
    view.offset = Math.max(0, view.offset - view.limit);
    renderCurrentSection();
  });
  const next = node("button", "button secondary", "Next page");
  next.type = "button";
  next.disabled = page.offset + page.items.length >= page.total;
  next.addEventListener("click", () => {
    view.offset += view.limit;
    renderCurrentSection();
  });
  append(pagination, previous, next);
  workspace.append(pagination);
}

function renderExport() {
  workspace.replaceChildren();
  workspace.append(titleBlock(
    "Canonical handoff",
    "Export reviewed selection",
    "Export reauthenticates the exact draft and template, validates complete selection bytes, and never modifies working state."
  ));
  const layout = node("div", "dashboard-grid");
  const panel = node("section", "panel");
  panel.append(
    view.bootstrap.review_complete
      ? node("p", "success-note", "The review is complete and eligible for canonical export.")
      : node("p", "warning", "Complete every applicable decision before export.")
  );
  if (!view.bootstrap.authoring_ready && view.bootstrap.review_complete) {
    panel.append(node("p", "danger-note", "The completed review contains blocking rejections. Export records them but authoring remains blocked."));
  }
  const exportButton = node("button", "button primary", "Validate and export exact selection");
  exportButton.type = "button";
  exportButton.disabled = !view.bootstrap.review_complete;
  const receipt = node("div");
  exportButton.addEventListener("click", () => runMutation(async () => {
    const envelope = await api("/api/export", {
      method: "POST",
      body: currentRevisionBody(),
    });
    receipt.replaceChildren(node("h3", "", "Validated export receipt"));
    const pre = node("pre");
    pre.textContent = JSON.stringify(envelope.result, null, 2);
    receipt.append(pre);
    showToast("Canonical reviewed selection exported.");
  }));
  append(panel, exportButton, receipt);
  const blockers = node("aside", "panel");
  blockers.append(node("h3", "", "Blocking rejection refs"));
  blockers.append(
    view.bootstrap.blocking_rejection_refs.length
      ? referenceList(view.bootstrap.blocking_rejection_refs)
      : node("p", "muted", "No blocking reviewed rejections.")
  );
  append(layout, panel, blockers);
  workspace.append(layout);
}

function showPreview(preview) {
  view.pendingPreview = preview;
  impactContent.replaceChildren();
  const summary = node("div", "metric-grid");
  append(
    summary,
    metric("Affected", preview.affected_refs.length),
    metric("Cleared", preview.cleared_refs.length),
    metric("Revision", preview.state_revision)
  );
  impactContent.append(summary);
  if (preview.decision_summary) {
    impactContent.append(node("p", "guided-lead", preview.decision_summary));
  }
  if (preview.requires_clear_confirmation) {
    impactContent.append(node(
      "p",
      "danger-note",
      "This action clears dependent decisions that are no longer applicable. Confirm only after reviewing every ref below."
    ));
  }
  const affected = node("details");
  affected.open = true;
  append(affected, node("summary", "", "Exact affected refs"), referenceList(preview.affected_refs));
  impactContent.append(affected);
  if (preview.cleared_refs.length) {
    const cleared = node("details");
    cleared.open = true;
    append(cleared, node("summary", "", "Dependent refs to clear"), referenceList(preview.cleared_refs));
    impactContent.append(cleared);
  }
  const counts = node("details");
  counts.append(node("summary", "", "Resulting review counts"));
  const pre = node("pre");
  pre.textContent = JSON.stringify(preview.resulting_counts, null, 2);
  counts.append(pre);
  impactContent.append(counts);
  confirmImpact.disabled = false;
  confirmImpact.textContent = preview.guided ? "Confirm and continue" : "Confirm exact action";
  impactDialog.showModal();
}

async function previewAction(action) {
  await runMutation(async () => {
    confirmImpact.disabled = true;
    const envelope = await api("/api/preview", {
      method: "POST",
      body: currentRevisionBody({action}),
    });
    showPreview(envelope.result);
  });
}

async function applyPending() {
  const preview = view.pendingPreview;
  if (!preview) return;
  await runMutation(async () => {
    await api("/api/apply", {
      method: "POST",
      body: {
        state_revision: preview.state_revision,
        preview_hash: preview.preview_hash,
      },
    });
    const guided = preview.guided === true;
    view.pendingPreview = null;
    showToast("Exact review action saved.");
    await refresh();
    if (guided) {
      view.guidedStarted = true;
      view.guidedPassStartRef = null;
      await loadGuidedNext(null);
    }
  });
}

async function runMutation(operation) {
  if (view.busy) return;
  setBusy(true);
  try {
    await operation();
  } catch (error) {
    await recover(error);
  } finally {
    setBusy(false);
  }
}

async function renderCurrentSection() {
  advancedNavigation.hidden = view.mode !== "advanced";
  guidedProgress.hidden = view.mode !== "guided";
  for (const button of modeNavigation) {
    if (button.dataset.mode === view.mode) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  }
  for (const button of navigation) {
    if (button.dataset.section === view.section) {
      button.setAttribute("aria-current", "page");
    } else {
      button.removeAttribute("aria-current");
    }
  }
  try {
    if (view.mode === "guided") {
      if (!view.guidedStarted) renderGuidedStart();
      else renderGuidedItem();
    } else if (view.section === "dashboard") renderDashboard();
    else if (view.section === "export") renderExport();
    else await renderItems();
  } catch (error) {
    await recover(error);
  }
  workspace.focus({preventScroll: true});
}

async function refresh() {
  const [envelope, guidedEnvelope] = await Promise.all([
    api("/api/bootstrap"),
    api("/api/guided/bootstrap"),
  ]);
  view.bootstrap = envelope.result;
  view.guidedBootstrap = guidedEnvelope.result;
  renderStatusHeader();
  await renderCurrentSection();
}

function renderFatal(message) {
  statusHeader.replaceChildren();
  navigation.forEach((button) => { button.disabled = true; });
  workspace.replaceChildren();
  const fatal = node("section", "fatal-state");
  append(
    fatal,
    node("p", "eyebrow", "Local session unavailable"),
    node("h2", "", "Review UI could not start"),
    node("p", "", message)
  );
  workspace.append(fatal);
}

impactDialog.addEventListener("close", () => {
  if (impactDialog.returnValue === "confirm") applyPending();
  else view.pendingPreview = null;
});

for (const button of navigation) {
  button.addEventListener("click", () => {
    view.section = button.dataset.section;
    view.offset = 0;
    renderCurrentSection();
  });
}

for (const button of modeNavigation) {
  button.addEventListener("click", () => switchMode(button.dataset.mode));
}

async function start() {
  if (!token) {
    renderFatal("The launch token is missing. Restart the local review server and use the complete printed launch address.");
    return;
  }
  try {
    await refresh();
  } catch (error) {
    renderFatal(`${error.message}. Restart the local review server and use its complete launch address.`);
  }
}

start();
