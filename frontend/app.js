import api from "./api.js";

// Global App State
const state = {
  user: null,
  activeView: "auth",
  activeChatWs: null,
  activeChatGameId: null,
  currentLatitude: null,
  currentLongitude: null
};

// UI Elements Cache
const el = {
  sidebar: document.getElementById("sidebar"),
  mainPanel: document.getElementById("mainPanel"),
  userBadge: document.getElementById("userBadge"),
  badgeName: document.getElementById("badgeName"),
  badgeKarma: document.getElementById("badgeKarma"),
  avatarLetter: document.getElementById("avatarLetter"),
  logoutBtn: document.getElementById("logoutBtn"),
  toastHolder: document.getElementById("toastHolder"),
  
  // Views
  views: {
    auth: document.getElementById("view-auth"),
    dashboard: document.getElementById("view-dashboard"),
    games: document.getElementById("view-games"),
    venues: document.getElementById("view-venues"),
    teams: document.getElementById("view-teams"),
    social: document.getElementById("view-social"),
    profile: document.getElementById("view-profile")
  }
};

// ==========================================
// 1. Toast Notifications Utility
// ==========================================
function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "toast-error" : type === "warning" ? "toast-warning" : ""}`;
  
  const icon = type === "error" ? "❌" : type === "warning" ? "⚠️" : "✓";
  
  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px;">
      <span style="font-size: 1.1rem;">${icon}</span>
      <span style="font-size: 0.9rem; font-weight: 500;">${message}</span>
    </div>
    <button style="background:transparent; border:none; color:var(--text-muted); cursor:pointer; font-size:1.1rem; padding-left:10px;" onclick="this.parentElement.remove()">&times;</button>
  `;
  
  el.toastHolder.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(50px)";
    toast.style.transition = "all 0.4s ease";
    setTimeout(() => toast.remove(), 400);
  }, 4000);
}

// ==========================================
// 2. Navigation & View Switcher
// ==========================================
function switchView(viewName) {
  if (!state.user && viewName !== "auth") {
    viewName = "auth";
  }
  
  state.activeView = viewName;
  
  // Close existing websocket if leaving chat/games
  if (viewName !== "games" && state.activeChatWs) {
    state.activeChatWs.close();
    state.activeChatWs = null;
    state.activeChatGameId = null;
    document.getElementById("active-game-chat-wrapper").style.display = "none";
  }
  
  // Update nav item active classes
  document.querySelectorAll(".nav-item").forEach(item => {
    if (item.getAttribute("data-view") === viewName) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });

  // Toggle view containers
  Object.keys(el.views).forEach(name => {
    if (name === viewName) {
      el.views[name].classList.add("active");
    } else {
      el.views[name].classList.remove("active");
    }
  });

  // Load view-specific content
  if (viewName === "dashboard") loadDashboard();
  else if (viewName === "games") loadGames();
  else if (viewName === "venues") loadVenues();
  else if (viewName === "teams") loadTeams();
  else if (viewName === "social") loadSocial();
  else if (viewName === "profile") loadProfile();
}

// ==========================================
// 3. Authentication Handlers
// ==========================================
function updateAuthUI() {
  state.user = api.getUser();
  
  if (state.user) {
    el.sidebar.style.display = "flex";
    el.mainPanel.style.marginLeft = "var(--sidebar-width)";
    el.mainPanel.style.width = "calc(100% - var(--sidebar-width))";
    
    // Fill badge details
    el.userBadge.style.display = "flex";
    el.badgeName.textContent = state.user.name;
    el.badgeKarma.textContent = `⚡ ${state.user.karma.toFixed(1)} Karma`;
    el.avatarLetter.textContent = state.user.name.charAt(0).toUpperCase();
    
    if (state.activeView === "auth") {
      switchView("dashboard");
    }
  } else {
    el.sidebar.style.display = "none";
    el.mainPanel.style.marginLeft = "0";
    el.mainPanel.style.width = "100%";
    el.userBadge.style.display = "none";
    switchView("auth");
  }
}

// Auth Tab switching
document.getElementById("switch-to-register").addEventListener("click", () => {
  const isLogin = document.getElementById("login-form").style.display !== "none";
  if (isLogin) {
    document.getElementById("login-form").style.display = "none";
    document.getElementById("register-form").style.display = "block";
    document.getElementById("auth-title").textContent = "Create an Account";
    document.getElementById("switch-prompt").innerHTML = 'Already have an account? <span id="switch-to-login">Log In</span>';
    
    document.getElementById("switch-to-login").addEventListener("click", () => {
      document.getElementById("login-form").style.display = "block";
      document.getElementById("register-form").style.display = "none";
      document.getElementById("auth-title").textContent = "Welcome to Turf";
      document.getElementById("switch-prompt").innerHTML = 'Don\'t have an account? <span id="switch-to-register">Sign Up</span>';
      // Re-bind click event recursively
      updateAuthUI();
    });
  }
});

// Login Form Submit
document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;
  
  try {
    await api.login(email, password);
    showToast("Logged in successfully!");
    updateAuthUI();
  } catch (error) {
    showToast(error.message, "error");
  }
});

// Register Form Submit
document.getElementById("register-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("register-name").value;
  const email = document.getElementById("register-email").value;
  const password = document.getElementById("register-password").value;
  const skill = document.getElementById("register-skill").value;
  const city = document.getElementById("register-city").value;
  
  try {
    await api.register(email, password, name, skill, city);
    showToast("Account created! You can now log in.");
    // Switch to login form
    document.getElementById("login-form").style.display = "block";
    document.getElementById("register-form").style.display = "none";
    document.getElementById("auth-title").textContent = "Welcome to Turf";
    document.getElementById("switch-prompt").innerHTML = 'Don\'t have an account? <span id="switch-to-register">Sign Up</span>';
  } catch (error) {
    showToast(error.message, "error");
  }
});

// Logout
el.logoutBtn.addEventListener("click", () => {
  api.logout();
  showToast("Logged out successfully");
  updateAuthUI();
});

// ==========================================
// 4. Dashboard Logic
// ==========================================
async function loadDashboard() {
  if (!state.user) return;
  
  document.getElementById("dash-username").textContent = state.user.name;
  document.getElementById("dash-karma-val").textContent = state.user.karma.toFixed(1);
  document.getElementById("dash-profile-city").textContent = state.user.city;
  document.getElementById("dash-profile-skill").textContent = state.user.skill_level;
  document.getElementById("dash-profile-email").textContent = state.user.email;
  document.getElementById("dash-profile-role").textContent = state.user.role;

  try {
    // 1. Fetch Games Nearby
    const games = await api.listGames({ city: state.user.city });
    document.getElementById("stat-active-games").textContent = games.length;

    // 2. Fetch User Bookings
    const bookings = await api.listBookings();
    const activeBookings = bookings.filter(b => b.status !== "cancelled");
    document.getElementById("stat-bookings").textContent = activeBookings.length;

    // 3. Fetch Followers Count
    const followers = await api.listFollowers(state.user.id);
    document.getElementById("stat-followers").textContent = followers.length;
  } catch (err) {
    console.error("Dashboard stats failed to load completely", err);
  }

  // 4. Fetch Notifications Feed (Module 9)
  try {
    const alerts = await api.listNotifications();
    const container = document.getElementById("dash-notifications-list");
    container.innerHTML = "";
    
    if (alerts.length === 0) {
      container.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 20px;">No new alerts.</div>`;
      return;
    }
    
    alerts.forEach(alert => {
      const card = document.createElement("div");
      card.className = `glass-card ${alert.read ? "" : "active"}`;
      card.style.display = "flex";
      card.style.justifyContent = "space-between";
      card.style.alignItems = "center";
      card.style.borderLeft = alert.read ? "1px solid var(--glass-border)" : "3px solid var(--primary)";
      
      card.innerHTML = `
        <div>
          <div style="font-weight:600; font-size:0.95rem; color:${alert.read ? "var(--text-muted)" : "var(--text-main)"}">${alert.title}</div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:2px;">${alert.body}</div>
        </div>
        ${!alert.read ? `<button class="btn btn-secondary" style="padding:4px 8px; font-size:0.75rem;" onclick="readAlert('${alert.id}')">Mark Read</button>` : ""}
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Notifications failed to load", err);
  }
}

window.readAlert = async function(id) {
  try {
    await api.markNotificationRead(id);
    loadDashboard();
    showToast("Notification marked read");
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ==========================================
// 5. Games Core Loop & Chat Logic
// ==========================================
async function loadGames() {
  const container = document.getElementById("games-list");
  container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 35px;">Searching game lobbies...</div>`;

  try {
    const filters = {
      sport: document.getElementById("filter-game-sport").value,
      city: document.getElementById("filter-game-city").value,
      status: document.getElementById("filter-game-status").value
    };

    const radius = document.getElementById("filter-game-radius").value;
    if (radius && state.currentLatitude !== null && state.currentLongitude !== null) {
      filters.lat = state.currentLatitude;
      filters.lng = state.currentLongitude;
      filters.radius_km = radius;
    }

    const games = await api.listGames(filters);
    container.innerHTML = "";

    if (games.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 35px;" class="glass-panel">No games found matching filters.</div>`;
      return;
    }

    games.forEach(game => {
      const isJoined = game.players && game.players.some(p => p.id === state.user.id);
      const isHost = game.host_id === state.user.id;
      
      const card = document.createElement("div");
      card.className = "glass-panel game-card";
      
      card.innerHTML = `
        <div class="card-main">
          <div class="card-title">${game.sport} Match</div>
          <div class="card-subtitle">
            <span>📍 ${game.city}</span>
            <span>👥 Slots Filled: ${game.slots_filled}/${game.max_players}</span>
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">
            Host ID: <span style="font-family:monospace; color:var(--accent); cursor:pointer;" onclick="followPlayerPrompt('${game.host_id}')">${game.host_id} (Follow Host)</span>
          </div>
        </div>
        <div style="display:flex; gap:10px; align-items:center;">
          <span class="badge ${game.status === "open" ? "badge-open" : "badge-full"}">${game.status}</span>
          ${isJoined 
            ? `<button class="btn btn-secondary" onclick="enterGameChat('${game.id}', '${game.sport}')">Chat Room</button>`
            : game.status === "open"
              ? `<button class="btn btn-primary" onclick="joinMatch('${game.id}')">Join Game</button>`
              : ""
          }
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div style="text-align: center; color: var(--danger); padding: 35px;">Error loading game lobbies: ${err.message}</div>`;
  }
}

window.followPlayerPrompt = async function(hostId) {
  if (hostId === state.user.id) {
    showToast("You are the host of this game!", "warning");
    return;
  }
  try {
    await api.followUser(hostId);
    showToast("Followed user successfully!");
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.joinMatch = async function(gameId) {
  try {
    await api.joinGame(gameId);
    showToast("Joined match! Auto-joining chat room...");
    loadGames();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// WebSocket Chat Connection (Module 6)
window.enterGameChat = function(gameId, sport) {
  const chatWrapper = document.getElementById("active-game-chat-wrapper");
  chatWrapper.style.display = "block";
  document.getElementById("chat-game-sport").textContent = sport;
  
  if (state.activeChatWs) {
    state.activeChatWs.close();
  }
  
  state.activeChatGameId = gameId;
  const messagesBox = document.getElementById("chat-messages-box");
  messagesBox.innerHTML = `<div style="color:var(--text-muted); font-size:0.8rem; text-align:center; padding:10px;">Connecting to chat server...</div>`;
  
  const wsUrl = api.getChatWebSocketUrl(gameId);
  const ws = new WebSocket(wsUrl);
  state.activeChatWs = ws;
  
  ws.onopen = () => {
    messagesBox.innerHTML = "";
  };
  
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    appendChatMessage(msg);
  };
  
  ws.onerror = (err) => {
    console.error("Chat WS Error", err);
    showToast("Chat WebSocket disconnected", "error");
  };
  
  ws.onclose = () => {
    console.log("Chat WS Closed");
  };
};

function appendChatMessage(msg) {
  const box = document.getElementById("chat-messages-box");
  const isSelf = msg.user_id === state.user.id;
  
  const row = document.createElement("div");
  row.className = `chat-msg-row ${isSelf ? "self" : ""}`;
  
  const formattedTime = new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  
  row.innerHTML = `
    <span class="chat-msg-sender">${isSelf ? "You" : msg.user_name}</span>
    <div class="chat-msg-bubble">${msg.body}</div>
    <span class="chat-msg-time">${formattedTime}</span>
  `;
  
  box.appendChild(row);
  box.scrollTop = box.scrollHeight; // Auto scroll
}

document.getElementById("chat-send-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const input = document.getElementById("chat-input-body");
  const body = input.value.trim();
  
  if (body && state.activeChatWs && state.activeChatWs.readyState === WebSocket.OPEN) {
    state.activeChatWs.send(JSON.stringify({ body }));
    input.value = "";
  }
});

// Nearby Radar filter geolocation setup
document.getElementById("filter-game-radius").addEventListener("change", (e) => {
  const radius = e.target.value;
  const coordsLabel = document.getElementById("radar-coordinates");
  
  if (radius) {
    coordsLabel.textContent = "Requesting position...";
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        state.currentLatitude = pos.coords.latitude;
        state.currentLongitude = pos.coords.longitude;
        coordsLabel.textContent = `Lat: ${pos.coords.latitude.toFixed(4)}, Lng: ${pos.coords.longitude.toFixed(4)}`;
        showToast("Browser location accessed successfully.");
      },
      (err) => {
        showToast("Failed to fetch browser location. Check permissions.", "error");
        e.target.value = "";
        coordsLabel.textContent = "Lat: Access Denied, Lng: Access Denied";
      }
    );
  } else {
    state.currentLatitude = null;
    state.currentLongitude = null;
    coordsLabel.textContent = "Lat: --, Lng: --";
  }
});

document.getElementById("btnFilterGames").addEventListener("click", () => {
  loadGames();
});

// Host Game triggers
document.getElementById("openHostModalBtn").addEventListener("click", async () => {
  toggleModal("modal-host-game", true);
  
  // Populate venues list options
  try {
    const venues = await api.listVenues();
    const select = document.getElementById("host-venue");
    select.innerHTML = '<option value="">No Venue / TBD</option>';
    venues.forEach(v => {
      select.innerHTML += `<option value="${v.id}">${v.name} (${v.city})</option>`;
    });

    // Populate team list options
    const teams = await api.listTeams();
    const teamSelect = document.getElementById("host-team");
    const teamGroup = document.getElementById("host-team-group");
    
    if (teams.length > 0) {
      teamGroup.style.display = "block";
      teamSelect.innerHTML = '<option value="">No Team (Individual Host)</option>';
      teams.forEach(t => {
        teamSelect.innerHTML += `<option value="${t.id}">${t.name}</option>`;
      });
    } else {
      teamGroup.style.display = "none";
    }
  } catch (err) {
    console.error("Failed to load options for hosting game", err);
  }
});

document.getElementById("host-game-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const sport = document.getElementById("host-sport").value;
  const city = document.getElementById("host-city").value;
  const capacity = document.getElementById("host-max-players").value;
  const venueId = document.getElementById("host-venue").value || null;
  const teamId = document.getElementById("host-team").value || null;
  
  try {
    await api.createGame(sport, city, parseInt(capacity), venueId, teamId);
    showToast("Match lobby hosted successfully!");
    toggleModal("modal-host-game", false);
    loadGames();
  } catch (err) {
    showToast(err.message, "error");
  }
});

// ==========================================
// 6. Venues & Booking Scheduler Logic
// ==========================================
async function loadVenues() {
  const container = document.getElementById("venues-list");
  container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 30px;">Loading physical venues...</div>`;
  
  try {
    const venues = await api.listVenues();
    container.innerHTML = "";
    
    if (venues.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 30px;" class="glass-panel">No venues registered in DB.</div>`;
      return;
    }
    
    venues.forEach(v => {
      const card = document.createElement("div");
      card.className = "glass-panel venue-card";
      
      card.innerHTML = `
        <div class="card-main">
          <div class="card-title">${v.name}</div>
          <div class="card-subtitle">
            <span>📍 ${v.address}, ${v.city}</span>
            <span>💸 INR ${v.hourly_rate}/hour</span>
          </div>
          <div style="font-size:0.8rem; color:var(--text-muted); margin-top:4px;">
            🕒 Operating Hours: ${v.opening_time} - ${v.closing_time}
          </div>
        </div>
        <button class="btn btn-primary" onclick="selectVenueForBooking('${v.id}', '${v.name}')">Select Slot</button>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div style="text-align: center; color: var(--danger); padding: 30px;">Error loading venues: ${err.message}</div>`;
  }
  
  loadUserBookings();
}

window.selectVenueForBooking = function(id, name) {
  document.getElementById("booking-venue-select-prompt").style.display = "none";
  const form = document.getElementById("booking-form");
  form.style.display = "block";
  
  document.getElementById("booking-venue-id").value = id;
  document.getElementById("booking-venue-name").value = name;
  document.getElementById("booking-panel-title").textContent = `Book Slot: ${name}`;
};

// Create Booking submit
document.getElementById("booking-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const venueId = document.getElementById("booking-venue-id").value;
  const startsAt = document.getElementById("booking-start").value;
  const endsAt = document.getElementById("booking-end").value;
  
  try {
    // 1. Create booking reservation
    const booking = await api.createBooking(venueId, startsAt, endsAt);
    showToast("Slot reserved successfully! Initializing payment checkout...");
    
    // 2. Trigger payment checkout logic
    processPaymentFlow(booking.id, booking.venue_id);
  } catch (err) {
    showToast(err.message, "error");
  }
});

// Razorpay Checkout Sequence (Module 5)
async function processPaymentFlow(bookingId, venueId) {
  try {
    // 1. Calculate amount & fetch payment details
    const orderDetails = await api.createPayment(bookingId, 2000.0); // pass dummy payment trigger
    showToast("Razorpay Payment captured! Processing webhook...");
    
    // 2. Mock calling the Razorpay callback webhook directly to confirm payment
    const payload = {
      event: "payment.captured",
      payload: {
        payment: {
          entity: {
            order_id: orderDetails.order.id,
            id: `pay_${Math.random().toString(36).substr(2, 9)}`
          }
        }
      }
    };
    
    // Fire webhook (since signature check runs on backend, this will fail if dummy keys are configured.
    // However, we capture that error and handle it informatively!)
    try {
      await api.verifyPayment(payload);
      showToast("Payment Successful! Booking confirmed.", "success");
    } catch (err) {
      showToast("Gateway Callback failed: signature check failed on local server. Updating visual status.", "warning");
      console.warn("Webhook failed (expected if local signature is verified with dummy keys)", err);
    }
    
    // Refresh lists
    loadUserBookings();
    loadDashboard();
  } catch (err) {
    showToast(`Payment Order creation failed: ${err.message}. Make sure real keys are configured in backend/.env if you want complete verification.`, "error");
    loadUserBookings();
  }
}

async function loadUserBookings() {
  const tbody = document.getElementById("user-bookings-table-body");
  
  try {
    const bookings = await api.listBookings();
    tbody.innerHTML = "";
    
    if (bookings.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="color: var(--text-muted); text-align: center; padding: 15px;">No bookings recorded.</td></tr>`;
      return;
    }
    
    bookings.forEach(b => {
      const startsDate = new Date(b.starts_at).toLocaleString();
      const tr = document.createElement("tr");
      
      tr.innerHTML = `
        <td style="font-weight:500; font-size:0.85rem;">Venue Slot</td>
        <td style="font-size:0.85rem; color:var(--text-muted);">${startsDate}</td>
        <td>
          <span class="booking-status-tag ${b.status}">${b.status}</span>
        </td>
        <td>
          ${b.status === "unpaid" 
            ? `<button class="btn btn-primary" style="padding:4px 8px; font-size:0.75rem;" onclick="payExistingBooking('${b.id}')">Pay</button>` 
            : ""
          }
          ${b.status !== "cancelled" 
            ? `<button class="btn btn-danger" style="padding:4px 8px; font-size:0.75rem; margin-left:4px;" onclick="cancelExistingBooking('${b.id}')">Cancel</button>`
            : ""
          }
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="4" style="color: var(--danger); text-align: center; padding: 15px;">Error: ${err.message}</td></tr>`;
  }
}

window.payExistingBooking = function(bookingId) {
  processPaymentFlow(bookingId);
};

window.cancelExistingBooking = async function(bookingId) {
  try {
    await api.cancelBooking(bookingId);
    showToast("Booking cancelled successfully.");
    loadUserBookings();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ==========================================
// 7. Teams Logic (Module 10)
// ==========================================
async function loadTeams() {
  const container = document.getElementById("teams-list");
  container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 30px;">Loading team directory...</div>`;
  
  try {
    const teams = await api.listTeams();
    container.innerHTML = "";
    
    if (teams.length === 0) {
      container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 30px;" class="glass-panel">No teams registered. Create one to begin!</div>`;
      return;
    }
    
    teams.forEach(t => {
      const card = document.createElement("div");
      card.className = "glass-panel venue-card";
      
      card.innerHTML = `
        <div class="card-main">
          <div class="card-title">${t.name}</div>
          <div class="card-subtitle">${t.description || "No description provided."}</div>
        </div>
        <button class="btn btn-secondary" onclick="viewTeamDetails('${t.id}')">View Club</button>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    container.innerHTML = `<div style="text-align: center; color: var(--danger); padding: 30px;">Error loading teams: ${err.message}</div>`;
  }
}

window.viewTeamDetails = async function(teamId) {
  const detailPanel = document.getElementById("team-detail-panel");
  detailPanel.style.display = "block";
  
  try {
    const team = await api.getTeam(teamId);
    document.getElementById("team-detail-name").textContent = team.name;
    document.getElementById("team-detail-desc").textContent = team.description || "No description.";
    
    const membersList = document.getElementById("team-members-list");
    membersList.innerHTML = "";
    
    let isMember = false;
    let userRole = "";
    
    team.members.forEach(member => {
      const isSelf = member.user_id === state.user.id;
      if (isSelf) {
        isMember = true;
        userRole = member.role;
      }
      
      const li = document.createElement("li");
      li.style.display = "flex";
      li.style.justifyContent = "space-between";
      li.style.alignItems = "center";
      li.innerHTML = `
        <span style="font-size:0.9rem; font-weight:500;">👤 ${member.name} ${isSelf ? "(You)" : ""}</span>
        <span class="badge badge-open" style="font-size:0.75rem;">${member.role}</span>
      `;
      membersList.appendChild(li);
    });
    
    // Add Join / Host Actions
    const hostActionWrapper = document.getElementById("team-action-host-game");
    if (isMember) {
      hostActionWrapper.style.display = "block";
      document.getElementById("teamHostGameBtn").onclick = () => {
        switchView("games");
        document.getElementById("openHostModalBtn").click();
        // preselect team in host selector after modal opens
        setTimeout(() => {
          document.getElementById("host-team").value = teamId;
        }, 150);
      };
    } else {
      hostActionWrapper.innerHTML = `<button class="btn btn-primary" style="width: 100%;" onclick="joinTeamClub('${teamId}')">Join Team Club</button>`;
      hostActionWrapper.style.display = "block";
    }
    
  } catch (err) {
    showToast(err.message, "error");
  }
};

window.joinTeamClub = async function(teamId) {
  try {
    await api.joinTeam(teamId);
    showToast("Successfully joined the team!");
    viewTeamDetails(teamId);
    loadTeams();
  } catch (err) {
    showToast(err.message, "error");
  }
};

document.getElementById("openTeamModalBtn").addEventListener("click", () => {
  toggleModal("modal-create-team", true);
});

document.getElementById("create-team-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("team-name").value;
  const desc = document.getElementById("team-desc").value;
  
  try {
    await api.createTeam(name, desc);
    showToast("New team registered successfully!");
    toggleModal("modal-create-team", false);
    loadTeams();
  } catch (err) {
    showToast(err.message, "error");
  }
});

// ==========================================
// 8. Social Network Logic
// ==========================================
async function loadSocial() {
  const feedContainer = document.getElementById("social-feed-list");
  feedContainer.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 25px;">Loading follow activity feed...</div>`;
  
  try {
    // 1. Load Activity Feed
    const feed = await api.getFollowFeed();
    feedContainer.innerHTML = "";
    
    if (feed.length === 0) {
      feedContainer.innerHTML = `<div style="color: var(--text-muted); text-align: center; padding: 25px;" class="glass-panel">Follow other players to see matching activities.</div>`;
    } else {
      feed.forEach(game => {
        const item = document.createElement("div");
        item.className = "glass-card";
        item.innerHTML = `
          <div style="font-weight:600; font-size:0.95rem; color:var(--primary);">Game Hosted by Followee</div>
          <div style="font-size:0.85rem; color:var(--text-muted); margin-top:4px;">Sport: ${game.sport} | City: ${game.city} | Status: ${game.status}</div>
        `;
        feedContainer.appendChild(item);
      });
    }
  } catch (err) {
    feedContainer.innerHTML = `<div style="color: var(--danger); text-align: center; padding: 25px;">Failed to load feed: ${err.message}</div>`;
  }
  
  // 2. Discover/Search user listing
  const discoverContainer = document.getElementById("social-players-list");
  discoverContainer.innerHTML = `<div style="color: var(--text-muted); padding:10px;">Finding players...</div>`;
  
  try {
    // Since we don't have list users endpoint, we display a manual ID follow trigger
    discoverContainer.innerHTML = `
      <div class="glass-panel" style="padding:15px; border-style:dashed;">
        <h4 style="font-size:0.95rem; margin-bottom:8px;">Follow by ID</h4>
        <div style="display:flex; gap:8px;">
          <input type="text" id="manual-follow-id" class="form-input" placeholder="Paste User UUID here...">
          <button class="btn btn-primary" onclick="triggerManualFollow()">Follow</button>
        </div>
        <p style="font-size:0.75rem; color:var(--text-muted); margin-top:8px;">You can copy another player's User UUID from a hosted game inside the Games Lobby.</p>
      </div>
      <div id="following-list-section" style="margin-top:20px;">
        <h4 style="font-size:0.95rem; margin-bottom:10px;">People you follow</h4>
        <ul id="following-users-list" style="list-style:none; display:flex; flex-direction:column; gap:8px;">
          <!-- Filled dynamically -->
        </ul>
      </div>
    `;
    
    loadFollowingList();
  } catch (err) {
    discoverContainer.innerHTML = `<div style="color: var(--danger); padding: 10px;">Failed to load search directory: ${err.message}</div>`;
  }
}

window.triggerManualFollow = async function() {
  const input = document.getElementById("manual-follow-id");
  const followId = input.value.trim();
  
  if (!followId) return;
  
  try {
    await api.followUser(followId);
    showToast("Followed user successfully!");
    input.value = "";
    loadSocial();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
};

async function loadFollowingList() {
  const list = document.getElementById("following-users-list");
  list.innerHTML = `<li style="font-size:0.8rem; color:var(--text-muted);">Loading follow list...</li>`;
  
  try {
    const following = await api.listFollowing(state.user.id);
    list.innerHTML = "";
    
    if (following.length === 0) {
      list.innerHTML = `<li style="font-size:0.8rem; color:var(--text-muted);">You are not following anyone yet.</li>`;
      return;
    }
    
    following.forEach(u => {
      const li = document.createElement("li");
      li.style.display = "flex";
      li.style.justifyContent = "space-between";
      li.style.alignItems = "center";
      li.style.background = "hsla(222, 47%, 10%, 0.4)";
      li.style.padding = "8px 12px";
      li.style.borderRadius = "8px";
      li.style.border = "1px solid var(--glass-border)";
      
      li.innerHTML = `
        <span style="font-size:0.85rem; font-weight:500;">👤 ${u.name} (${u.city})</span>
        <button class="btn btn-danger" style="padding:2px 6px; font-size:0.75rem;" onclick="unfollowPlayer('${u.id}')">Unfollow</button>
      `;
      list.appendChild(li);
    });
  } catch (err) {
    list.innerHTML = `<li style="font-size:0.8rem; color:var(--danger);">Failed to load follow list: ${err.message}</li>`;
  }
}

window.unfollowPlayer = async function(id) {
  try {
    await api.unfollowUser(id);
    showToast("Unfollowed player successfully.");
    loadSocial();
    loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
};

// ==========================================
// 9. Profile Settings Logic
// ==========================================
function loadProfile() {
  if (!state.user) return;
  document.getElementById("profile-name").value = state.user.name;
  document.getElementById("profile-city").value = state.user.city;
  document.getElementById("profile-skill").value = state.user.skill_level;
  document.getElementById("profile-karma-val").textContent = state.user.karma.toFixed(1);
}

document.getElementById("profile-update-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const name = document.getElementById("profile-name").value;
  const city = document.getElementById("profile-city").value;
  const skill = document.getElementById("profile-skill").value;
  
  try {
    await api.updateProfile({ name, city, skill_level: skill });
    showToast("Profile settings updated!");
  } catch (err) {
    showToast(err.message, "error");
  }
});

// ==========================================
// 10. Modals Helper & Listeners
// ==========================================
window.toggleModal = function(modalId, show) {
  const modal = document.getElementById(modalId);
  if (show) modal.classList.add("active");
  else modal.classList.remove("active");
};

// Auto-align sidebar navigation clicks
document.querySelectorAll(".nav-item").forEach(item => {
  item.addEventListener("click", (e) => {
    e.preventDefault();
    const view = item.getAttribute("data-view");
    switchView(view);
  });
});

// Ratings Modal trigger helper (Module 7)
window.openRatingModal = function(gameId, userId, name) {
  toggleModal("modal-rate-player", true);
  document.getElementById("rate-game-id").value = gameId;
  document.getElementById("rate-user-id").value = userId;
  document.getElementById("rate-target-name").textContent = name;
  
  // Clear stars
  document.querySelectorAll(".rating-star-btn").forEach(btn => {
    btn.classList.remove("active");
  });
  document.getElementById("rate-score-input").value = "";
};

document.querySelectorAll(".rating-star-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const val = parseInt(btn.getAttribute("data-val"));
    document.getElementById("rate-score-input").value = val;
    
    document.querySelectorAll(".rating-star-btn").forEach(b => {
      const bVal = parseInt(b.getAttribute("data-val"));
      if (bVal <= val) b.classList.add("active");
      else b.classList.remove("active");
    });
  });
});

document.getElementById("rate-player-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const gameId = document.getElementById("rate-game-id").value;
  const userId = document.getElementById("rate-user-id").value;
  const score = document.getElementById("rate-score-input").value;
  const comment = document.getElementById("rate-comment").value;
  
  if (!score) {
    showToast("Please choose a star score!", "warning");
    return;
  }
  
  try {
    await api.rateUser(gameId, userId, parseInt(score), comment);
    showToast("Rating submitted! User karma recalculating.");
    toggleModal("modal-rate-player", false);
    
    // Refresh
    if (state.activeView === "dashboard") loadDashboard();
  } catch (err) {
    showToast(err.message, "error");
  }
});

// App Bootstrap Init
window.addEventListener("auth-changed", () => {
  updateAuthUI();
});

// Check login status on page boot
async function initApp() {
  const token = api.getToken();
  if (token) {
    try {
      const user = await api.getCurrentUser();
      api.setUser(user);
    } catch (err) {
      // Token expired, clear
      api.setToken(null);
      api.setUser(null);
    }
  }
  updateAuthUI();
}

initApp();
export {};
