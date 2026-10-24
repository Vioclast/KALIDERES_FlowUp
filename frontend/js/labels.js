/** Each kind of suggestion gets its own colour band on the label. */
function tagVariant(suggestion) {
  if (suggestion.action === "discount") {
    return "tag--discount";
  }
  if (suggestion.action === "needs_review") {
    return "tag--review";
  }
  return suggestion.priority === "high" ? "tag--urgent" : "tag--normal";
}

function tagHeadline(suggestion) {
  if (suggestion.action === "reorder") {
    return `Order ${suggestion.suggested_quantity} more`;
  }
  if (suggestion.action === "discount") {
    return `Sell at ${suggestion.discount_percent}% off`;
  }
  return "A person needs to decide";
}

/** The big number on the tear-off part of the label. */
function tagFigure(suggestion) {
  if (suggestion.action === "reorder") {
    return { number: String(suggestion.suggested_quantity), caption: "units to order" };
  }
  if (suggestion.action === "discount") {
    return { number: `${suggestion.discount_percent}%`, caption: "discount" };
  }
  return { number: "?", caption: "your call" };
}

function tagMoneyNote(suggestion) {
  if (suggestion.estimated_amount === null) {
    return "";
  }
  if (suggestion.action === "reorder") {
    return `Order cost about ${money.format(suggestion.estimated_amount)}`;
  }
  if (suggestion.action === "discount") {
    return `About ${money.format(suggestion.estimated_amount)} of stock at risk`;
  }
  return "";
}

function approveLabel(suggestion) {
  if (suggestion.action === "discount") {
    return "Approve discount";
  }
  if (suggestion.action === "reorder") {
    return "Approve order";
  }
  return "Place order";
}

/** The message shown after the owner decided. It uses the same words as the buttons. */
function decisionMessage(suggestion, decision, payload) {
  const name = suggestion.product_name;

  if (decision === "reject") {
    const verb = suggestion.action === "needs_review" ? "Dismissed" : "Rejected";
    return `${verb}: ${name}. It may be suggested again at the next stock check.`;
  }
  if (suggestion.action === "discount") {
    return `Approved: ${suggestion.discount_percent}% discount applied to ${name}.`;
  }
  const quantity = payload ? payload.quantity : suggestion.suggested_quantity;
  return `Approved: order placed for ${quantity} units of ${name}.`;
}

function setBusy(actionsEl, busy) {
  for (const button of actionsEl.querySelectorAll("button")) {
    button.disabled = busy;
  }
}

/** Human approval: send the owner's decision to the server, then refresh the page. */
async function decide(suggestion, decision, actionsEl, quantityInput) {
  let options = { method: "POST" };

  if (decision === "approve" && quantityInput !== null) {
    const quantity = Number(quantityInput.value);
    if (!Number.isInteger(quantity) || quantity < 1) {
      showToast("error", "Enter how many units to order, for example 24.");
      quantityInput.focus();
      return;
    }
    options = { method: "POST", json: { quantity } };
  }

  setBusy(actionsEl, true);
  try {
    await api(`/recommendations/${suggestion.id}/${decision}`, options);
    showToast("ok", decisionMessage(suggestion, decision, options.json));
  } catch (error) {
    showToast("error", error.message);
  }

  loadBriefing({ quiet: true });
}

/** The buttons at the bottom of a label. Only the owner gets them. */
function createActions(suggestion) {
  const actions = document.createElement("div");
  actions.className = "tag__actions";

  if (state.currentUser.role !== "owner") {
    const hint = document.createElement("p");
    hint.className = "tag__hint";
    hint.textContent = "Only the owner can approve or reject.";
    actions.append(hint);
    return actions;
  }

  const isReview = suggestion.action === "needs_review";
  const needsQuantity = isReview && suggestion.batch_id === null;
  const canApprove = !isReview || needsQuantity;

  let quantityInput = null;
  if (needsQuantity) {
    const field = document.createElement("label");
    field.className = "tag__quantity";
    field.append("Units to order");

    quantityInput = document.createElement("input");
    quantityInput.type = "number";
    quantityInput.min = "1";
    quantityInput.step = "1";
    quantityInput.inputMode = "numeric";

    field.append(quantityInput);
    actions.append(field);
  }

  if (canApprove) {
    const approve = document.createElement("button");
    approve.type = "button";
    approve.className = "button";
    approve.textContent = approveLabel(suggestion);
    approve.addEventListener("click", () =>
      decide(suggestion, "approve", actions, quantityInput),
    );
    actions.append(approve);
  }

  const reject = document.createElement("button");
  reject.type = "button";
  reject.className = "button button--quiet";
  reject.textContent = isReview ? "Dismiss" : "Reject";
  reject.addEventListener("click", () => decide(suggestion, "reject", actions, null));
  actions.append(reject);

  return actions;
}

function createTag(suggestion) {
  const tag = document.createElement("li");
  tag.className = `tag ${tagVariant(suggestion)}`;

  const band = document.createElement("div");
  band.className = "tag__band";
  band.setAttribute("aria-hidden", "true");

  const body = document.createElement("div");
  body.className = "tag__body";

  const name = document.createElement("h3");
  name.className = "tag__name";
  name.textContent = suggestion.product_name;
  if (suggestion.priority === "high") {
    const flag = document.createElement("span");
    flag.className = "tag__flag";
    flag.textContent = "Urgent";
    name.append(flag);
  }

  const action = document.createElement("p");
  action.className = "tag__action";
  action.textContent = tagHeadline(suggestion);

  const reason = document.createElement("p");
  reason.className = "tag__reason";
  reason.textContent = suggestion.reason;

  body.append(name, action, reason);

  const moneyNote = tagMoneyNote(suggestion);
  if (moneyNote) {
    const note = document.createElement("p");
    note.className = "tag__money";
    note.textContent = moneyNote;
    body.append(note);
  }

  body.append(createActions(suggestion));

  const figure = tagFigure(suggestion);
  const figureEl = document.createElement("div");
  figureEl.className = "tag__figure";

  const number = document.createElement("span");
  number.className = "tag__number";
  number.textContent = figure.number;

  const caption = document.createElement("span");
  caption.className = "tag__caption";
  caption.textContent = figure.caption;

  figureEl.append(number, caption);
  tag.append(band, body, figureEl);
  return tag;
}

/** The "Needs a decision" part of the page, with the stock check button. */
function renderSuggestionsSection(suggestions) {
  const section = document.createElement("section");
  section.setAttribute("aria-labelledby", "suggestions-title");

  const head = document.createElement("div");
  head.className = "section-head";

  const title = document.createElement("h2");
  title.id = "suggestions-title";
  title.textContent = "Needs a decision";

  const runButton = document.createElement("button");
  runButton.type = "button";
  runButton.className = suggestions.length === 0 ? "button" : "button button--quiet";
  runButton.textContent = "Run stock check";
  runButton.addEventListener("click", () => runStockCheck(runButton));

  head.append(title, runButton);
  section.appendChild(head);

  if (suggestions.length === 0) {
    const empty = document.createElement("div");
    empty.className = "notice notice--calm";

    const emptyTitle = document.createElement("strong");
    emptyTitle.textContent = "Nothing to decide yet.";

    const emptyText = document.createElement("p");
    emptyText.textContent = "Run a stock check to find items that need reordering or a discount.";

    empty.append(emptyTitle, emptyText);
    section.appendChild(empty);
    return section;
  }

  const list = document.createElement("ul");
  list.className = "tags";
  for (const suggestion of suggestions) {
    list.appendChild(createTag(suggestion));
  }
  section.appendChild(list);
  return section;
}

/** Trigger: ask the server to check all stock and save new suggestions. */
async function runStockCheck(button) {
  button.disabled = true;
  button.textContent = "Checking stock...";

  try {
    const created = await api("/recommendations/run", { method: "POST" });
    const text =
      created.length === 0
        ? "Stock check finished. Nothing new to suggest."
        : `Stock check finished. ${pluralize(created.length, "new suggestion")} added.`;
    showToast("ok", text);
  } catch (error) {
    showToast("error", error.message);
  }

  loadBriefing({ quiet: true });
}