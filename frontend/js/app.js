const STORAGE_KEY = "flowup.currentUserId";

const ROLE_LABELS = {
  owner: "Owner",
  warehouse: "Warehouse staff",
  cashier: "Cashier",
};

const money = new Intl.NumberFormat("en-MY", { style: "currency", currency: "MYR" });

const state = {
  users: [],
  currentUser: null,
};

const switcherEl = document.getElementById("user-switcher");
const appEl = document.getElementById("app");

let toastTimer = null;

/** The pages of the app. The address in the browser (for example #orders) picks one. */
const ROUTES = {
  briefing: () => loadBriefing(),
  stock: () => renderStockSoon(),
  orders: () => loadOrders(),
  activity: () => loadActivity(),
};

function pluralize(count, word) {
  return `${count} ${word}${count === 1 ? "" : "s"}`;
}

/** Show a short message at the bottom of the screen after the user did something. */
function showToast(kind, text) {
  const toast = document.getElementById("toast");
  toast.className = `toast toast--${kind}`;
  toast.textContent = text;
  toast.hidden = false;

  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toast.hidden = true;
  }, 8000);
}

/** Remember which user was selected, even after the page is reloaded. */
function loadSavedUserId() {
  try {
    return Number(localStorage.getItem(STORAGE_KEY));
  } catch (error) {
    return 0;
  }
}

function saveUserId(id) {
  try {
    localStorage.setItem(STORAGE_KEY, String(id));
  } catch (error) {
    // Storage can be blocked by the browser. The app still works without it.
  }
}

/**
 * Call the backend. Every request carries the id of the user who is signed in.
 * Pass { json: {...} } to send data in the request body.
 */
async function api(path, options = {}) {
  const { json, ...fetchOptions } = options;

  const headers = {};
  if (state.currentUser) {
    headers["x-user-id"] = String(state.currentUser.id);
  }
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    fetchOptions.body = JSON.stringify(json);
  }

  let response;
  try {
    response = await fetch(path, { ...fetchOptions, headers });
  } catch (error) {
    throw new Error("Cannot reach the FlowUp server. Check that it is running.");
  }

  if (!response.ok) {
    let message = "Something went wrong. Please try again.";
    try {
      const body = await response.json();
      if (typeof body.detail === "string") {
        message = body.detail;
      }
    } catch (error) {
      // The response had no readable message. Keep the default one.
    }
    const failure = new Error(message);
    failure.status = response.status;
    throw failure;
  }

  return response.json();
}

/** Which page the address in the browser asks for. Unknown addresses open the briefing. */
function getRoute() {
  const name = window.location.hash.replace("#", "");
  return Object.hasOwn(ROUTES, name) ? name : "briefing";
}

/** True while the page the user asked for is still the one that should be on screen. */
function stillOn(route, user) {
  return getRoute() === route && state.currentUser === user;
}

function markActiveNav(route) {
  for (const link of document.querySelectorAll(".main-nav a")) {
    if (link.getAttribute("href") === `#${route}`) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
}

function showCurrentPage() {
  if (state.currentUser === null) {
    return;
  }
  const route = getRoute();
  markActiveNav(route);
  ROUTES[route]();
}

function renderSwitcher() {
  switcherEl.innerHTML = "";

  for (const user of state.users) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "nametag";
    button.setAttribute("aria-pressed", String(user.id === state.currentUser.id));

    const name = document.createElement("span");
    name.className = "nametag-name";
    name.textContent = user.name;

    const role = document.createElement("span");
    role.className = "nametag-role";
    role.textContent = ROLE_LABELS[user.role] || user.role;

    button.append(name, role);
    button.addEventListener("click", () => switchUser(user));
    switcherEl.appendChild(button);
  }
}

function renderError(error) {
  appEl.innerHTML = "";

  const notice = document.createElement("div");
  notice.className = "notice";
  notice.setAttribute("role", "alert");

  const title = document.createElement("strong");
  title.textContent =
    error.status === 403
      ? "This page is not available for your role."
      : "This page could not be loaded.";

  const detail = document.createElement("p");
  detail.textContent = error.message;

  notice.append(title, detail);
  appEl.appendChild(notice);
}

function createFigure(label, value) {
  const wrapper = document.createElement("div");
  wrapper.className = "figure";

  const term = document.createElement("dt");
  term.textContent = label;

  const description = document.createElement("dd");
  description.textContent = value;

  wrapper.append(term, description);
  return wrapper;
}

function renderBriefing(summary, suggestions) {
  appEl.innerHTML = "";

  const waiting = summary.pending_recommendations;
  const verdict = document.createElement("h1");
  verdict.className = "verdict";
  if (waiting === 0) {
    verdict.textContent = "No suggestions are waiting for a decision.";
  } else {
    const verb = waiting === 1 ? "suggestion is" : "suggestions are";
    verdict.textContent = `${waiting} ${verb} waiting for a decision.`;
  }

  const figures = document.createElement("dl");
  figures.className = "figures";
  figures.append(
    createFigure("Stock value (at cost)", money.format(summary.stock_value)),
    createFigure("Products below minimum stock", String(summary.low_stock_products)),
    createFigure("Units expiring within 7 days", String(summary.units_expiring_soon)),
  );

  // Only the owner receives this number from the server.
  if (summary.total_order_spend !== null) {
    figures.append(
      createFigure("Spent on supplier orders", money.format(summary.total_order_spend)),
    );
  }

  appEl.append(verdict, figures, renderSuggestionsSection(suggestions));
}

/** Load the briefing. With { quiet: true } the page is refreshed without a loading message. */
async function loadBriefing({ quiet = false } = {}) {
  const user = state.currentUser;

  if (!quiet) {
    appEl.innerHTML = '<p class="status">Loading the shop briefing...</p>';
  }

  try {
    const [summary, suggestions] = await Promise.all([
      api("/dashboard/summary"),
      api("/recommendations?status=pending"),
    ]);
    if (!stillOn("briefing", user)) {
      return;
    }
    renderBriefing(summary, suggestions);
  } catch (error) {
    if (!stillOn("briefing", user)) {
      return;
    }
    renderError(error);
  }
}

function switchUser(user) {
  state.currentUser = user;
  saveUserId(user.id);
  renderSwitcher();
  showCurrentPage();
}

async function init() {
  try {
    state.users = await api("/users");
  } catch (error) {
    renderError(error);
    return;
  }

  if (state.users.length === 0) {
    renderError(new Error("No users found. Run the seed script to create the demo data."));
    return;
  }

  const savedId = loadSavedUserId();
  state.currentUser =
    state.users.find((user) => user.id === savedId) ||
    state.users.find((user) => user.role === "owner") ||
    state.users[0];

  renderSwitcher();
  showCurrentPage();
}

window.addEventListener("hashchange", () => {
  window.scrollTo(0, 0);
  showCurrentPage();
});

init();