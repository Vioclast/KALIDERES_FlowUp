/** Format a time sent by the server, for example "24 Oct 2026, 11:05 pm". */
function formatTime(isoText) {
  const date = new Date(isoText);
  if (Number.isNaN(date.getTime())) {
    return isoText;
  }
  return date.toLocaleString("en-MY", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function capitalize(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function createSectionHead(id, titleText) {
  const head = document.createElement("div");
  head.className = "section-head";

  const title = document.createElement("h2");
  title.id = id;
  title.textContent = titleText;

  head.appendChild(title);
  return head;
}

function createVerdict(text) {
  const verdict = document.createElement("h1");
  verdict.className = "verdict";
  verdict.textContent = text;
  return verdict;
}

function createNote(text) {
  const note = document.createElement("p");
  note.className = "page-note";
  note.textContent = text;
  return note;
}

/* ---------- Orders ---------- */

function createSlip(order, isOwner) {
  const slip = document.createElement("li");
  slip.className = "slip";

  const main = document.createElement("div");

  const head = document.createElement("div");
  head.className = "slip__head";

  const name = document.createElement("h3");
  name.className = "slip__name";
  name.textContent = order.product_name;

  const chip = document.createElement("span");
  chip.className = "chip";
  chip.textContent = capitalize(order.status);

  head.append(name, chip);

  const line = document.createElement("p");
  line.className = "slip__line";
  line.textContent = `${pluralize(order.quantity, "unit")} from ${order.supplier_name}`;

  const approver = state.users.find((user) => user.id === order.approved_by_user_id);
  let metaText = `Placed ${formatTime(order.created_at)}`;
  if (approver) {
    metaText += ` · Approved by ${approver.name}`;
  }

  const meta = document.createElement("p");
  meta.className = "slip__meta";
  meta.textContent = metaText;

  main.append(head, line, meta);
  slip.appendChild(main);

  // Money is shown to the owner only, the same rule as on the briefing page.
  if (isOwner) {
    const cost = document.createElement("div");
    cost.className = "slip__cost";

    const amount = document.createElement("span");
    amount.className = "slip__amount";
    amount.textContent = money.format(Number(order.total_cost) || 0);

    const caption = document.createElement("span");
    caption.className = "slip__caption";
    caption.textContent = "order cost";

    cost.append(amount, caption);
    slip.appendChild(cost);
  }

  return slip;
}

function renderOrders(orders) {
  appEl.innerHTML = "";

  const isOwner = state.currentUser.role === "owner";
  const newestFirst = [...orders].sort((a, b) => b.id - a.id);

  const verdict = createVerdict(
    newestFirst.length === 0
      ? "No supplier orders have been placed yet."
      : `${pluralize(newestFirst.length, "supplier order")} placed so far.`,
  );

  const unitsOrdered = newestFirst.reduce((sum, order) => sum + order.quantity, 0);
  const figures = document.createElement("dl");
  figures.className = "figures";
  figures.append(
    createFigure("Orders placed", String(newestFirst.length)),
    createFigure("Units ordered", String(unitsOrdered)),
  );
  if (isOwner) {
    const spent = newestFirst.reduce((sum, order) => sum + (Number(order.total_cost) || 0), 0);
    figures.append(createFigure("Spent on supplier orders", money.format(spent)));
  }

  const section = document.createElement("section");
  section.setAttribute("aria-labelledby", "orders-title");
  section.appendChild(createSectionHead("orders-title", "Order history"));
  section.appendChild(createNote("An order is created when the owner approves a reorder suggestion."));

  if (newestFirst.length === 0) {
    const empty = document.createElement("div");
    empty.className = "notice notice--calm";

    const emptyTitle = document.createElement("strong");
    emptyTitle.textContent = "Nothing to show yet.";

    const emptyText = document.createElement("p");
    emptyText.textContent = "Approve a reorder suggestion on the briefing page and the order will appear here.";

    const back = document.createElement("a");
    back.className = "button";
    back.href = "#briefing";
    back.textContent = "Go to the briefing";

    empty.append(emptyTitle, emptyText, back);
    section.appendChild(empty);
  } else {
    const list = document.createElement("ul");
    list.className = "slips";
    for (const order of newestFirst) {
      list.appendChild(createSlip(order, isOwner));
    }
    section.appendChild(list);
  }

  appEl.append(verdict, figures, section);
}

async function loadOrders() {
  const user = state.currentUser;
  appEl.innerHTML = '<p class="status">Loading supplier orders...</p>';

  try {
    const orders = await api("/orders");
    if (!stillOn("orders", user)) {
      return;
    }
    renderOrders(orders);
  } catch (error) {
    if (!stillOn("orders", user)) {
      return;
    }
    renderError(error);
  }
}

/* ---------- Activity log ---------- */

const ACTION_LABELS = {
  recommendation_approved: "Approved a suggestion",
  recommendation_rejected: "Rejected a suggestion",
};

/** Turn the code stored by the server into a readable sentence. */
function describeAction(action) {
  if (ACTION_LABELS[action]) {
    return ACTION_LABELS[action];
  }
  return capitalize(action.replace(/_/g, " "));
}

function entryVariant(action) {
  if (action.includes("approved")) {
    return "entry--approved";
  }
  if (action.includes("rejected")) {
    return "entry--rejected";
  }
  return "entry--other";
}

function createEntry(entry) {
  const item = document.createElement("li");
  item.className = `entry ${entryVariant(entry.action)}`;

  const time = document.createElement("p");
  time.className = "entry__time";
  time.textContent = formatTime(entry.timestamp);

  const card = document.createElement("div");
  card.className = "entry__card";

  const action = document.createElement("p");
  action.className = "entry__action";
  action.textContent = describeAction(entry.action);

  const who = document.createElement("p");
  who.className = "entry__who";
  who.textContent = `${entry.user_name} · ${ROLE_LABELS[entry.role] || entry.role}`;

  const details = document.createElement("p");
  details.className = "entry__details";
  details.textContent = entry.details;

  card.append(action, who, details);
  item.append(time, card);
  return item;
}

function renderActivity(entries) {
  appEl.innerHTML = "";

  const newestFirst = [...entries].sort((a, b) => b.id - a.id);

  const verdict = createVerdict(
    newestFirst.length === 0
      ? "Nothing has been recorded yet."
      : `${pluralize(newestFirst.length, "action")} recorded, newest first.`,
  );

  const section = document.createElement("section");
  section.setAttribute("aria-labelledby", "activity-title");
  section.appendChild(createSectionHead("activity-title", "Activity log"));
  section.appendChild(createNote("Who did what, and when. Only the owner can see this page."));

  if (newestFirst.length === 0) {
    const empty = document.createElement("div");
    empty.className = "notice notice--calm";

    const emptyTitle = document.createElement("strong");
    emptyTitle.textContent = "No activity yet.";

    const emptyText = document.createElement("p");
    emptyText.textContent = "Approve or reject a suggestion and it will be written here.";

    empty.append(emptyTitle, emptyText);
    section.appendChild(empty);
  } else {
    const list = document.createElement("ol");
    list.className = "timeline";
    for (const entry of newestFirst) {
      list.appendChild(createEntry(entry));
    }
    section.appendChild(list);
  }

  appEl.append(verdict, section);
}

async function loadActivity() {
  const user = state.currentUser;
  appEl.innerHTML = '<p class="status">Loading the activity log...</p>';

  try {
    const entries = await api("/activity-log");
    if (!stillOn("activity", user)) {
      return;
    }
    renderActivity(entries);
  } catch (error) {
    if (!stillOn("activity", user)) {
      return;
    }
    renderError(error);
  }
}

/* ---------- Stock (built in the next step) ---------- */

function renderStockSoon() {
  appEl.innerHTML = "";

  const notice = document.createElement("div");
  notice.className = "notice notice--calm";

  const title = document.createElement("strong");
  title.textContent = "The stock page is coming next.";

  const text = document.createElement("p");
  text.textContent = "It will list every product with its stock level and expiry dates.";

  notice.append(title, text);
  appEl.appendChild(notice);
}