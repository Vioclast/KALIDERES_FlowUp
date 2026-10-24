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
    const money = document.createElement("p");
    money.className = "tag__money";
    money.textContent = moneyNote;
    body.append(money);
  }

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

  if (state.flash) {
    const flash = document.createElement("p");
    flash.className = `flash flash--${state.flash.kind}`;
    flash.setAttribute("role", state.flash.kind === "error" ? "alert" : "status");
    flash.textContent = state.flash.text;
    section.appendChild(flash);
    state.flash = null;
  }

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
    state.flash = { kind: "ok", text };
  } catch (error) {
    state.flash = { kind: "error", text: error.message };
  }

  loadBriefing();
}