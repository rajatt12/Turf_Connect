import api from "./api.js?t=1788339500";

// Global App State
const state = {
  user: null,
  activeView: "auth",
  selectedCity: "Mumbai",
  activeChatWs: null,
  activeChatGame: null,
  venuesCache: [],
  teamsCache: [],
  selectedSportFilter: ""
};

// UI Selectors Cache
const el = {
  viewAuth: document.getElementById("view-auth"),
  mainApp: document.getElementById("main-app"),
  authModalCard: document.getElementById("auth-modal-card"),
  quickDevLoginBtn: document.getElementById("quick-dev-login-btn"),
  popupDevLoginBtn: document.getElementById("popup-dev-login-btn"),
  logoutBtn: document.getElementById("logout-btn"),
  toastHolder: document.getElementById("toast-holder"),

  // Dashboard elements
  dashGreeting: document.getElementById("dash-greeting"),
  dashTodayDate: document.getElementById("dash-today-date"),
  dashAthleteName: document.getElementById("dash-athlete-name"),
  dashAthleteCity: document.getElementById("dash-athlete-city"),
  dashAthleteSkill: document.getElementById("dash-athlete-skill"),
  dashAthleteKarma: document.getElementById("dash-athlete-karma"),
  dashAvatarLetter: document.getElementById("dash-avatar-letter"),
  vsFighter2: document.getElementById("vs-fighter-2"),

  views: {
    dashboard: document.getElementById("view-dashboard"),
    games: document.getElementById("view-games"),
    venues: document.getElementById("view-venues"),
    teams: document.getElementById("view-teams"),
    social: document.getElementById("view-social"),
    profile: document.getElementById("view-profile")
  },

  chatDrawer: document.getElementById("chat-drawer"),
  chatGameTitle: document.getElementById("chat-game-title"),
  chatMessagesBox: document.getElementById("chat-messages-box"),
  chatSendForm: document.getElementById("chat-send-form"),
  chatInputField: document.getElementById("chat-input-field")
};

// ====================================================================
// 1. Toast Notifications
// ====================================================================
function showToast(message, type = "success") {
  if (!el.toastHolder) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "toast-error" : type === "warning" ? "toast-warning" : ""}`;
  
  const icon = type === "error" ? "❌" : type === "warning" ? "⚠️" : "🎾";
  
  toast.innerHTML = `
    <div style="display: flex; align-items: center; gap: 10px;">
      <span style="font-size: 1.1rem;">${icon}</span>
      <span style="font-size: 0.9rem; font-weight: 600;">${message}</span>
    </div>
    <button style="background:transparent; border:none; color:rgba(255,255,255,0.6); cursor:pointer; font-size:1.1rem; margin-left:auto;" onclick="this.parentElement.remove()">&times;</button>
  `;
  
  el.toastHolder.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(40px)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}
window.showToast = showToast;

// ====================================================================
// 2. Auth Modal Toggle & View Switcher
// ====================================================================
function toggleAuthModal(open = true) {
  if (el.authModalCard) {
    if (open) {
      el.authModalCard.classList.add("open");
    } else {
      el.authModalCard.classList.remove("open");
    }
  }
}
window.toggleAuthModal = toggleAuthModal;

function switchView(viewName) {
  if (!state.user && viewName !== "auth") {
    viewName = "auth";
  }

  state.activeView = viewName;

  if (viewName === "auth") {
    el.viewAuth.style.display = "flex";
    el.mainApp.style.display = "none";
    toggleAuthModal(false);
    return;
  }

  el.viewAuth.style.display = "none";
  el.mainApp.style.display = "flex";

  // Update nav item active classes
  document.querySelectorAll(".match-nav-item").forEach(link => {
    if (link.getAttribute("data-view") === viewName) {
      link.classList.add("active");
    } else {
      link.classList.remove("active");
    }
  });

  // Toggle view containers
  Object.keys(el.views).forEach(name => {
    if (el.views[name]) {
      if (name === viewName) {
        el.views[name].classList.add("active");
      } else {
        el.views[name].classList.remove("active");
      }
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
window.switchView = switchView;

// ====================================================================
// 3. Auth & State Handlers
// ====================================================================
function updateAuthUI() {
  state.user = api.getUser();

  if (state.user) {
    // Populate dynamic date
    const now = new Date();
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    if (el.dashTodayDate) el.dashTodayDate.textContent = `TODAY IS ${now.toLocaleDateString('en-US', options).toUpperCase()}`;

    // Populate user profile info in Bento
    if (el.dashGreeting) el.dashGreeting.textContent = `Welcome ${state.user.name.split(' ')[0]}!`;
    if (el.dashAthleteName) el.dashAthleteName.textContent = state.user.name;
    if (el.dashAthleteCity) el.dashAthleteCity.textContent = `🌐 ${state.user.city.toUpperCase()}, INDIA`;
    if (el.dashAthleteSkill) el.dashAthleteSkill.textContent = state.user.skill_level || "Intermediate";
    if (el.dashAthleteKarma) el.dashAthleteKarma.textContent = `⚡ ${(state.user.karma || 5.0).toFixed(1)} / 5.0`;
    if (el.dashAvatarLetter) el.dashAvatarLetter.textContent = state.user.name.charAt(0).toUpperCase();
    if (el.vsFighter2) el.vsFighter2.textContent = state.user.name;

    if (state.user.city) state.selectedCity = state.user.city;

    // Show Register Arena only for Admin or Venue Owners
    const registerVenueBtn = document.getElementById("btn-register-venue");
    if (registerVenueBtn) {
      if (state.user.role === "admin" || state.user.role === "venue_owner") {
        registerVenueBtn.style.display = "inline-flex";
      } else {
        registerVenueBtn.style.display = "none";
      }
    }

    if (state.activeView === "auth") {
      switchView("dashboard");
    } else {
      loadDashboard();
    }
  } else {
    switchView("auth");
  }
}

// 1-Click Dev Demo Login
const triggerDevLogin = async () => {
  try {
    showToast("Connecting with pro dev credentials...");
    await api.login("dev@example.com", "devpassword123");
    showToast("Welcome to SquadUp, Dev User!");
    updateAuthUI();
  } catch (err) {
    showToast(err.message, "error");
  }
};

if (el.quickDevLoginBtn) el.quickDevLoginBtn.addEventListener("click", triggerDevLogin);
if (el.popupDevLoginBtn) el.popupDevLoginBtn.addEventListener("click", triggerDevLogin);

// Standard Login Form
const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    try {
      await api.login(email, password);
      showToast("Signed in successfully!");
      updateAuthUI();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// Register Form
const registerForm = document.getElementById("register-form");
if (registerForm) {
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("register-name").value;
    const email = document.getElementById("register-email").value;
    const password = document.getElementById("register-password").value;
    const skill = document.getElementById("register-skill").value;
    const city = document.getElementById("register-city").value;

    try {
      await api.register(email, password, name, skill, city);
      showToast("Account created! Logging in...");
      await api.login(email, password);
      updateAuthUI();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// Switch between Login and Register tabs
const authSwitchBtn = document.getElementById("auth-switch-btn");
const authSwitchText = document.getElementById("auth-switch-text");
if (authSwitchBtn) {
  authSwitchBtn.addEventListener("click", () => {
    const isLoginVisible = loginForm.style.display !== "none";
    if (isLoginVisible) {
      loginForm.style.display = "none";
      registerForm.style.display = "block";
      authSwitchText.textContent = "Already have an account?";
      authSwitchBtn.textContent = "Log In";
    } else {
      loginForm.style.display = "block";
      registerForm.style.display = "none";
      authSwitchText.textContent = "Don't have an account?";
      authSwitchBtn.textContent = "Sign Up";
    }
  });
}

// Logout
if (el.logoutBtn) {
  el.logoutBtn.addEventListener("click", () => {
    api.logout();
    if (state.activeChatWs) {
      state.activeChatWs.close();
      state.activeChatWs = null;
    }
    showToast("Signed out successfully");
    updateAuthUI();
  });
}

// City Selector Change Listener
const citySelector = document.getElementById("global-city-selector");
if (citySelector) {
  citySelector.addEventListener("change", (e) => {
    state.selectedCity = e.target.value;
    showToast(`Filtered circuit for ${state.selectedCity}`);
    if (state.activeView === "dashboard") loadDashboard();
    else if (state.activeView === "games") loadGames();
    else if (state.activeView === "venues") loadVenues();
  });
}

// Sidebar Navigation
document.querySelectorAll(".match-nav-item").forEach(link => {
  link.addEventListener("click", (e) => {
    e.preventDefault();
    const targetView = link.getAttribute("data-view");
    if (targetView) switchView(targetView);
  });
});

// ====================================================================
// 4. View Loaders: Bento Dashboard
// ====================================================================
async function loadDashboard() {
  if (!state.user) return;

  try {
    const [allGames, venues, followers] = await Promise.all([
      api.listGames(),
      api.listVenues(state.selectedCity),
      api.getFollowers(state.user.id).catch(() => [])
    ]);

    state.venuesCache = venues || [];
    const gamesList = allGames || [];

    // Filter games the user is in
    const myGames = gamesList.filter(g => g.players && g.players.some(p => p.id === state.user.id));
    const myUpcomingGame = myGames.find(g => g.status !== "completed");
    const myCompletedGames = myGames.filter(g => g.status === "completed");

    // Dynamic Topbar Badges
    const pillFollowers = document.getElementById("pill-followers");
    if (pillFollowers) {
      const fCount = followers ? followers.length : 0;
      pillFollowers.textContent = `${fCount} FOLLOWERS`;
    }

    const pillMatches = document.getElementById("pill-matches");
    if (pillMatches) {
      pillMatches.textContent = `${myGames.length} MATCHES`;
    }

    // Dynamic "My Next Match" Card
    const nextMatchDateEl = document.getElementById("next-match-date");
    const vsFighter1El = document.getElementById("vs-fighter-1");
    const vsFighter2El = document.getElementById("vs-fighter-2");

    if (myUpcomingGame) {
      let timeFormatted = "UPCOMING MATCH";
      if (myUpcomingGame.starts_at) {
        const dt = new Date(myUpcomingGame.starts_at);
        timeFormatted = dt.toLocaleDateString("en-US", { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).toUpperCase();
      }
      if (nextMatchDateEl) nextMatchDateEl.textContent = timeFormatted;
      if (vsFighter1El) vsFighter1El.innerHTML = `${myUpcomingGame.sport} Lobby<div style="font-size: 11px; color: var(--primary-lime); font-weight: 700;">📍 ${myUpcomingGame.city} • ${myUpcomingGame.slots_filled || 1}/${myUpcomingGame.max_players} PLAYERS</div>`;
      if (vsFighter2El) vsFighter2El.innerHTML = `${state.user.name}<div style="font-size: 11px; color: #F59E0B; font-weight: 700;">⚡ ${myUpcomingGame.skill_level || 'Open Match'}</div>`;
    } else {
      if (nextMatchDateEl) nextMatchDateEl.textContent = "READY TO COMPETE";
      if (vsFighter1El) vsFighter1El.innerHTML = `Open Match Lobbies<div style="font-size: 11px; color: var(--primary-lime); font-weight: 700;">FIND PICKUP PLAYERS</div>`;
      if (vsFighter2El) vsFighter2El.innerHTML = `${state.user.name}<div style="font-size: 11px; color: #F59E0B; font-weight: 700;">HOST A MATCH</div>`;
    }

    // Dynamic Career Performance
    const statBigWinsEl = document.getElementById("stat-big-wins");
    const statRatioText = document.getElementById("stat-ratio-text");
    if (statBigWinsEl) {
      statBigWinsEl.textContent = `${myCompletedGames.length} Matches`;
    }
    if (statRatioText) {
      statRatioText.textContent = myCompletedGames.length > 0 ? `[ Active Competitor ]` : `[ Ready to Compete ]`;
    }

    // Dynamic Latest Scores Box
    const liveScoreTitle = document.getElementById("live-score-title");
    const liveScoreSub = document.getElementById("live-score-sub");
    const liveScoreTag = document.getElementById("live-score-tag");

    if (liveScoreTitle && liveScoreSub && liveScoreTag) {
      if (myCompletedGames.length > 0) {
        const last = myCompletedGames[myCompletedGames.length - 1];
        liveScoreTitle.textContent = `🏆 ${last.sport.toUpperCase()} MATCH`;
        liveScoreSub.textContent = `Completed match in ${last.city}`;
        liveScoreTag.textContent = "COMPLETED";
      } else {
        liveScoreTitle.textContent = `⚡ PICKUP MATCHES`;
        liveScoreSub.textContent = `Play your first match to record scores!`;
        liveScoreTag.textContent = "NEW ROSTER";
      }
    }

    // Sport Breakdown Counts
    const cricketCount = myGames.filter(g => g.sport === "Cricket").length;
    const footballCount = myGames.filter(g => g.sport === "Football").length;
    const racketCount = myGames.filter(g => g.sport === "Badminton" || g.sport === "Tennis").length;

    const winsSinglesEl = document.getElementById("wins-singles");
    const winsDoublesEl = document.getElementById("wins-doubles");
    const winsMixedEl = document.getElementById("wins-mixed");

    if (winsSinglesEl) winsSinglesEl.textContent = `${cricketCount} Matches`;
    if (winsDoublesEl) winsDoublesEl.textContent = `${footballCount} Matches`;
    if (winsMixedEl) winsMixedEl.textContent = `${racketCount} Matches`;

  } catch (err) {
    console.error("Dashboard calculation error:", err);
  }
}

// ====================================================================
// 5. View Loaders: Games Loop (Matchmaking)
// ====================================================================
function renderGameCardHtml(game) {
  const isJoined = state.user && game.players && game.players.some(p => p.id === state.user.id);
  const isHost = state.user && game.host_id === state.user.id;
  const slotsFilled = game.slots_filled || (game.players ? game.players.length : 1);
  const maxPlayers = game.max_players || 4;
  const hostPlayer = game.players ? game.players.find(p => p.id === game.host_id) : null;

  const sportIcons = {
    Football: "⚽",
    Cricket: "🏏",
    Badminton: "🏸",
    Basketball: "🏀",
    Tennis: "🎾"
  };
  const icon = sportIcons[game.sport] || "🎾";

  // Format date if available
  let timeStr = "Open Pickup Lobby";
  if (game.starts_at) {
    const dt = new Date(game.starts_at);
    timeStr = dt.toLocaleDateString("en-US", { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  }

  return `
    <div class="hub-card" style="display: flex; flex-direction: column; gap: 12px; border: 1px solid rgba(0,0,0,0.06); position: relative;">
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <span style="font-weight: 800; font-size: 14px;">${icon} ${game.sport.toUpperCase()}</span>
        <div style="display: flex; gap: 6px; align-items: center;">
          ${isHost ? `<span style="background: rgba(210, 238, 56, 0.25); color: #233015; border: 1px solid rgba(210, 238, 56, 0.5); padding: 2px 8px; border-radius: var(--radius-full); font-size: 10px; font-weight: 800;">👑 YOU ARE HOST</span>` : ''}
          <span style="background: rgba(0,0,0,0.06); color: var(--text-dark); padding: 3px 8px; border-radius: var(--radius-full); font-size: 10px; font-weight: 700;">${game.skill_level || 'All Levels'}</span>
          <span style="background: ${game.status === 'open' ? 'var(--primary-lime)' : '#000'}; color: ${game.status === 'open' ? '#121812' : '#FFF'}; padding: 3px 10px; border-radius: var(--radius-full); font-size: 11px; font-weight: 800; text-transform: uppercase;">${game.status}</span>
        </div>
      </div>

      <div>
        <div style="font-size: 17px; font-weight: 800; color: var(--text-dark);">${game.sport} Pickup Match</div>
        <div style="font-size: 12px; color: var(--text-dark-muted); margin-top: 2px;">📅 ${timeStr}</div>
        <div style="font-size: 12px; color: var(--text-dark-muted); margin-top: 1px;">📍 ${game.city} • ${!isHost && hostPlayer ? `Hosted by <b>${hostPlayer.name}</b>` : 'Open Community Match'}</div>
      </div>

      <!-- Joined Players Roster List -->
      <div style="background: rgba(0,0,0,0.03); border-radius: var(--radius-md); padding: 10px 12px;">
        <div style="font-size: 10px; font-weight: 800; color: var(--text-dark-muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em;">
          👥 Joined Roster (${slotsFilled}/${maxPlayers})
        </div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
          ${(game.players || []).map(p => `
            <div style="background: #FFF; border: 1px solid var(--border-light); border-radius: var(--radius-full); padding: 3px 10px; display: flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 700;">
              <span style="width: 18px; height: 18px; border-radius: 50%; background: ${p.id === game.host_id ? 'var(--primary-lime)' : '#E2E8F0'}; display: flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 800; color: #121812;">
                ${p.name ? p.name.charAt(0).toUpperCase() : 'P'}
              </span>
              <span>${state.user && p.id === state.user.id ? 'You' : (p.name || 'Player')}</span>
              ${p.id === game.host_id ? '<span style="font-size: 9px; color: #D97706; font-weight: 800;">👑 HOST</span>' : ''}
            </div>
          `).join('')}
          ${Array.from({ length: Math.max(0, maxPlayers - slotsFilled) }).map(() => `
            <div style="border: 1px dashed rgba(0,0,0,0.18); border-radius: var(--radius-full); padding: 3px 8px; font-size: 10px; color: var(--text-dark-muted); font-weight: 600;">
              + Open Slot
            </div>
          `).join('')}
        </div>
      </div>

      <div style="display: flex; gap: 8px; margin-top: auto; flex-wrap: wrap;">
        ${!isJoined && game.status === "open" ? `
          <button type="button" class="btn-coral-journey" style="flex: 1; font-size: 12px; padding: 8px 16px;" onclick="handleJoinGame('${game.id}')">Join Match</button>
        ` : ''}
        ${isJoined ? `
          <button type="button" class="btn-lime-dev" style="flex: 1; font-size: 12px; padding: 8px 14px;" onclick="openChatDrawer('${game.id}', '${game.sport} Match Lobby')">
            💬 Live Chat
          </button>
        ` : ''}
        ${isJoined && !isHost ? `
          <button type="button" class="filter-pill-canvas" style="font-size: 11px; padding: 6px 12px; color: var(--primary-coral);" onclick="handleLeaveGame('${game.id}')">Leave</button>
        ` : ''}
        ${isHost && game.status !== "completed" ? `
          <button type="button" class="filter-pill-canvas" style="font-size: 11px; padding: 6px 10px;" onclick="handleCompleteGame('${game.id}')">End & Rate</button>
          <button type="button" class="filter-pill-canvas" style="font-size: 11px; padding: 6px 10px; color: var(--primary-coral);" onclick="handleCancelGame('${game.id}')">Cancel</button>
        ` : ''}
        ${game.status === "completed" && isJoined ? `
          <button type="button" class="btn-coral-journey" style="flex: 1; font-size: 12px; padding: 8px 12px;" onclick="openRateGameModalById('${game.id}')">⭐ Rate Match Players</button>
        ` : ''}
      </div>
    </div>
  `;
}

async function loadGames() {
  const container = document.getElementById("games-grid-container");
  if (!container) return;
  container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 40px; grid-column: 1/-1;">Loading active match lobbies...</div>`;

  try {
    const filters = { city: state.selectedCity };
    if (state.selectedSportFilter) filters.sport = state.selectedSportFilter;

    const games = await api.listGames(filters);
    if (!games || games.length === 0) {
      container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 60px; grid-column: 1/-1; font-weight: 600;">No active match lobbies in ${state.selectedCity}. Be the first to host!</div>`;
      return;
    }

    container.innerHTML = games.map(g => renderGameCardHtml(g)).join("");
  } catch (err) {
    container.innerHTML = `<div style="color: var(--primary-coral); text-align: center; padding: 40px; grid-column: 1/-1;">Failed to load games: ${err.message}</div>`;
  }
}

// Sport Filters in Games Loop
const gamesSportFilterGroup = document.getElementById("games-sport-filters");
if (gamesSportFilterGroup) {
  gamesSportFilterGroup.querySelectorAll(".filter-pill-canvas").forEach(pill => {
    pill.addEventListener("click", () => {
      gamesSportFilterGroup.querySelectorAll(".filter-pill-canvas").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      state.selectedSportFilter = pill.getAttribute("data-sport") || "";
      loadGames();
    });
  });
}

// Join Game Handler
async function handleJoinGame(gameId) {
  try {
    await api.joinGame(gameId);
    showToast("Joined match! Auto-connecting to live game lobby...");
    loadGames();
    openChatDrawer(gameId, "Match Lobby");
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleJoinGame = handleJoinGame;

// Leave Game Handler
async function handleLeaveGame(gameId) {
  try {
    await api.leaveGame(gameId);
    showToast("Left match roster.");
    loadGames();
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleLeaveGame = handleLeaveGame;

// Cancel Game Handler
async function handleCancelGame(gameId) {
  if (!confirm("Are you sure you want to cancel this match lobby?")) return;
  try {
    await api.cancelGame(gameId);
    showToast("Match lobby cancelled.");
    loadGames();
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleCancelGame = handleCancelGame;

// Complete Game Handler
async function handleCompleteGame(gameId) {
  try {
    const completedGame = await api.completeGame(gameId);
    showToast("Match completed! Opening karma sportsmanship review...");
    loadGames();
    openRateGameModal(completedGame);
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleCompleteGame = handleCompleteGame;

function openRateGameModal(game) {
  const gameIdInput = document.getElementById("rate-game-id");
  const playerSelect = document.getElementById("rate-player-select");
  if (gameIdInput) gameIdInput.value = game.id;

  const currentUserId = state.user ? state.user.id : null;
  const otherPlayers = (game.players || []).filter(p => p.id !== currentUserId);

  if (playerSelect) {
    if (otherPlayers.length === 0) {
      playerSelect.innerHTML = `<option value="">No other players to rate</option>`;
    } else {
      playerSelect.innerHTML = otherPlayers.map(p => `<option value="${p.id}">👤 ${p.name || 'Athlete'}</option>`).join("");
    }
  }

  openModal("modal-rate-game");
}
window.openRateGameModal = openRateGameModal;

async function openRateGameModalById(gameId) {
  try {
    const game = await api.getGame(gameId);
    openRateGameModal(game);
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.openRateGameModalById = openRateGameModalById;

const rateGameForm = document.getElementById("rate-game-form");
if (rateGameForm) {
  rateGameForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const gameId = document.getElementById("rate-game-id").value;
    const ratedId = document.getElementById("rate-player-select").value;
    const score = document.getElementById("rate-score-select").value;
    const comment = document.getElementById("rate-comment-input").value;

    if (!ratedId) {
      showToast("Please select a player to rate.", "error");
      return;
    }

    try {
      showToast("Submitting sportsmanship review...");
      await api.ratePlayer(gameId, ratedId, score, comment);
      showToast("Karma score submitted successfully! ⚡");
      closeModal("modal-rate-game");
      loadGames();
      loadProfile();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// ====================================================================
// 6. View Loaders: Turf Venues & Booking
// ====================================================================
function renderVenueCardHtml(venue) {
  return `
    <div class="hub-card" style="display: flex; flex-direction: column; gap: 14px;">
      <div style="height: 120px; background: linear-gradient(135deg, #1A241A, #101610); border-radius: var(--radius-md); padding: 12px; display: flex; align-items: flex-end; justify-content: space-between;">
        <span style="background: #141C12; color: var(--primary-lime); font-weight: 800; font-size: 13px; padding: 4px 10px; border-radius: var(--radius-full);">₹${venue.hourly_rate} / hr</span>
        <span style="background: rgba(255,255,255,0.1); color: #FFF; font-weight: 700; font-size: 11px; padding: 3px 8px; border-radius: var(--radius-full);">${venue.sports ? venue.sports.join(', ') : 'Multi-Sport'}</span>
      </div>
      <div>
        <div style="font-size: 18px; font-weight: 800;">${venue.name}</div>
        <div style="font-size: 12px; color: var(--text-dark-muted); margin-top: 2px;">📍 ${venue.address}, ${venue.city}</div>
      </div>
      <div style="display: flex; gap: 8px; margin-top: auto;">
        <button type="button" class="btn-coral-journey" style="flex: 1; padding: 8px 12px; font-size: 12px;" onclick="openBookVenueModal('${venue.id}', '${venue.name}', ${venue.hourly_rate})">
          Reserve Slot
        </button>
        <button type="button" class="btn-lime-dev" style="padding: 8px 12px; font-size: 12px;" onclick="openHostGameModal('${venue.id}')" title="Host a match at this arena">
          + Host Match
        </button>
      </div>
    </div>
  `;
}

async function loadVenues() {
  const container = document.getElementById("venues-grid-container");
  if (!container) return;
  container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 40px; grid-column: 1/-1;">Loading courts & venues...</div>`;

  try {
    const venues = await api.listVenues(state.selectedCity);
    state.venuesCache = venues || [];

    if (!venues || venues.length === 0) {
      container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 60px; grid-column: 1/-1;">No turf venues registered in ${state.selectedCity}.</div>`;
    } else {
      container.innerHTML = venues.map(v => renderVenueCardHtml(v)).join("");
    }

    loadMyBookings();
  } catch (err) {
    container.innerHTML = `<div style="color: var(--primary-coral); text-align: center; padding: 40px; grid-column: 1/-1;">Failed to load venues: ${err.message}</div>`;
  }
}

async function loadMyBookings() {
  const container = document.getElementById("my-bookings-container");
  if (!container) return;

  try {
    const bookings = await api.listBookings();
    if (!bookings || bookings.length === 0) {
      container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 20px;">You have no active court reservations.</div>`;
      return;
    }

    container.innerHTML = bookings.map(b => `
      <div style="background: rgba(0,0,0,0.03); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 14px; margin-bottom: 10px; display: flex; align-items: center; justify-content: space-between;">
        <div>
          <div style="font-weight: 800; font-size: 14px;">Court Booking #${b.id.substring(0, 8)}</div>
          <div style="color: var(--text-dark-muted); font-size: 12px;">${new Date(b.starts_at).toLocaleString()} &rarr; ${new Date(b.ends_at).toLocaleTimeString()}</div>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="font-weight: 800; font-size: 11px; text-transform: uppercase; padding: 4px 10px; border-radius: var(--radius-full); background: ${b.status === 'paid' ? 'var(--primary-lime)' : '#000'}; color: ${b.status === 'paid' ? '#121812' : '#FFF'};">${b.status}</span>
          ${b.status === 'unpaid' ? `<button class="btn-coral-journey" style="padding: 4px 12px; font-size: 11px;" onclick="handlePayBooking('${b.id}')">Pay</button>` : ''}
          ${b.status !== 'cancelled' ? `<button class="filter-pill-canvas" style="padding: 4px 10px; font-size: 11px;" onclick="handleCancelBooking('${b.id}')">Cancel</button>` : ''}
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.error("Bookings error:", err);
  }
}

// ====================================================================
// 7. View Loaders: Teams & Social Feed
// ====================================================================
async function loadTeams() {
  const container = document.getElementById("teams-grid-container");
  if (!container) return;
  container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 40px; grid-column: 1/-1;">Loading sports clubs...</div>`;

  try {
    const teams = await api.listTeams();
    state.teamsCache = teams || [];

    if (!teams || teams.length === 0) {
      container.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 60px; grid-column: 1/-1;">No teams registered yet. Start the first club!</div>`;
      return;
    }

    container.innerHTML = teams.map(t => `
      <div class="hub-card" style="display: flex; flex-direction: column; gap: 12px;">
        <h3 style="font-size: 18px; font-weight: 800;">${t.name}</h3>
        <p style="color: var(--text-dark-muted); font-size: 13px;">${t.description || 'Sports club community'}</p>
        <button class="btn-lime-dev" style="margin-top: auto; font-size: 12px; padding: 8px 16px;" onclick="handleJoinTeam('${t.id}')">Join Club Roster</button>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div style="color: var(--primary-coral); text-align: center; padding: 40px; grid-column: 1/-1;">Failed to load teams: ${err.message}</div>`;
  }
}

async function handleJoinTeam(teamId) {
  try {
    await api.joinTeam(teamId);
    showToast("Joined team club roster!");
    loadTeams();
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleJoinTeam = handleJoinTeam;

async function loadSocial() {
  const directoryContainer = document.getElementById("athletes-directory-container");
  const feedContainer = document.getElementById("social-activity-feed");

  if (!state.user) return;

  if (directoryContainer) {
    directoryContainer.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 20px;">Loading athletes directory...</div>`;
  }

  try {
    const [allAthletes, followingUsers, recentGames] = await Promise.all([
      api.listUsers().catch(() => []),
      api.getFollowing(state.user.id).catch(() => []),
      api.listGames({ city: state.selectedCity }).catch(() => [])
    ]);

    const followingSet = new Set((followingUsers || []).map(u => u.id));
    const currentCity = (state.selectedCity || "").toLowerCase();

    // Filter out logged-in user and sort athletes in current city first
    const athletesList = (allAthletes || [])
      .filter(u => u.id !== state.user.id)
      .sort((a, b) => {
        const aInCity = (a.city || "").toLowerCase() === currentCity ? 1 : 0;
        const bInCity = (b.city || "").toLowerCase() === currentCity ? 1 : 0;
        return bInCity - aInCity;
      });

    // 1. Render Discover Athletes Directory
    if (directoryContainer) {
      if (athletesList.length === 0) {
        directoryContainer.innerHTML = `<div style="color: var(--text-dark-muted); text-align: center; padding: 30px;">No other registered athletes found. Invite friends to connect!</div>`;
      } else {
        directoryContainer.innerHTML = athletesList.map(athlete => {
          const isFollowing = followingSet.has(athlete.id);
          const initial = athlete.name ? athlete.name.charAt(0).toUpperCase() : "A";
          return `
            <div style="background: rgba(0,0,0,0.03); border: 1px solid var(--border-light); border-radius: var(--radius-md); padding: 12px 14px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
              <div style="display: flex; align-items: center; gap: 12px;">
                <div class="athlete-thumb" style="width: 38px; height: 38px; font-size: 14px; background: var(--accent-dark-card); color: var(--primary-lime); border: 1.5px solid rgba(16, 185, 129, 0.4);">${initial}</div>
                <div>
                  <div style="font-weight: 800; font-size: 14px; color: var(--text-dark);">${athlete.name}</div>
                  <div style="font-size: 11px; color: var(--text-dark-muted); margin-top: 2px;">
                    ${athlete.skill_level || 'Intermediate'} • 📍 ${athlete.city} • <span style="color: #D97706; font-weight: 700;">⚡ ${(athlete.karma || 5.0).toFixed(1)}</span>
                  </div>
                </div>
              </div>
              <button type="button" class="filter-pill-canvas ${isFollowing ? 'active' : ''}" style="font-size: 11px; padding: 6px 14px; font-weight: 700;" onclick="handleToggleFollow('${athlete.id}', ${isFollowing})">
                ${isFollowing ? 'Following ✓' : '+ Follow'}
              </button>
            </div>
          `;
        }).join("");
      }
    }

    // 2. Render Live Activity Feed
    if (feedContainer) {
      const activities = [];
      (recentGames || []).forEach(g => {
        const hostName = g.players && g.players.length > 0 ? g.players[0].name : "Host";
        if (g.status === "completed") {
          activities.push(`🏆 <b>${hostName}</b> completed a ${g.sport} match in ${g.city}!`);
        } else {
          activities.push(`🔥 <b>${hostName}</b> launched an open ${g.sport} pickup lobby (${g.slots_filled || 1}/${g.max_players} players).`);
        }
      });

      if (activities.length === 0) {
        feedContainer.innerHTML = `
          <div style="background: rgba(0,0,0,0.03); border-radius: var(--radius-md); padding: 20px; font-size: 13px; text-align: center; color: var(--text-dark-muted);">
            No recent activity in ${state.selectedCity}. Host a game to start the feed!
          </div>
        `;
      } else {
        feedContainer.innerHTML = activities.slice(0, 8).map(act => `
          <div style="background: rgba(0,0,0,0.03); border-radius: var(--radius-md); padding: 12px 14px; font-size: 13px; margin-bottom: 8px; color: var(--text-dark); border-left: 3px solid var(--accent-turf-green);">
            ${act}
          </div>
        `).join("");
      }
    }
  } catch (err) {
    if (directoryContainer) directoryContainer.innerHTML = `<div style="color: var(--primary-coral); text-align: center; padding: 20px;">Failed to load social network: ${err.message}</div>`;
  }
}

// Follow / Unfollow Handler
async function handleToggleFollow(userId, isFollowing) {
  try {
    if (isFollowing) {
      await api.unfollowUser(userId);
      showToast("Unfollowed athlete.");
    } else {
      await api.followUser(userId);
      showToast("Followed athlete! Added to your pickup circle.");
    }
    loadSocial();
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleToggleFollow = handleToggleFollow;

// ====================================================================
// 8. View Loaders: Profile & Settings
// ====================================================================
function loadProfile() {
  if (!state.user) return;
  const nameInput = document.getElementById("prof-name");
  const skillSelect = document.getElementById("prof-skill");
  const cityInput = document.getElementById("prof-city");
  const karmaBig = document.getElementById("prof-karma-big");

  if (nameInput) nameInput.value = state.user.name || "";
  if (skillSelect) skillSelect.value = state.user.skill_level || "Intermediate";
  if (cityInput) cityInput.value = state.user.city || "Mumbai";
  if (karmaBig) karmaBig.textContent = `⚡ ${(state.user.karma || 5.0).toFixed(1)}`;
}

const profileEditForm = document.getElementById("profile-edit-form");
if (profileEditForm) {
  profileEditForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("prof-name").value;
    const skill_level = document.getElementById("prof-skill").value;
    const city = document.getElementById("prof-city").value;

    try {
      showToast("Saving profile...");
      const updatedUser = await api.updateProfile({ name, skill_level, city });
      if (updatedUser) {
        state.user = updatedUser;
      }
      showToast("Profile settings saved!");
      updateAuthUI();
      loadProfile();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// ====================================================================
// 9. Live WebSocket Game Lobby Chat Drawer
// ====================================================================
function openChatDrawer(gameId, title = "Game Lobby") {
  if (state.activeChatWs) {
    state.activeChatWs.close();
    state.activeChatWs = null;
  }

  state.activeChatGame = gameId;
  if (el.chatGameTitle) el.chatGameTitle.textContent = title;
  if (el.chatDrawer) el.chatDrawer.style.display = "flex";
  if (el.chatMessagesBox) {
    el.chatMessagesBox.innerHTML = `<div style="color: rgba(255,255,255,0.6); font-size: 12px; text-align: center; margin-top: 10px;">Connected to match lobby. Say hello! 👋</div>`;
  }

  try {
    const wsUrl = api.getChatWebSocketUrl(gameId);
    state.activeChatWs = new WebSocket(wsUrl);

    state.activeChatWs.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        appendChatMessage(msg);
      } catch (e) {
        console.error("Chat parse error:", e);
      }
    };
  } catch (err) {
    console.error("Chat WebSocket error:", err);
  }
}
window.openChatDrawer = openChatDrawer;

function closeChatDrawer() {
  if (state.activeChatWs) {
    state.activeChatWs.close();
    state.activeChatWs = null;
  }
  if (el.chatDrawer) el.chatDrawer.style.display = "none";
}
window.closeChatDrawer = closeChatDrawer;

function appendChatMessage(msg) {
  if (!el.chatMessagesBox) return;
  const isMine = state.user && (msg.user_id === state.user.id || msg.user_name === state.user.name || msg.sender === state.user.name);
  const bubble = document.createElement("div");
  bubble.style.maxWidth = "80%";
  bubble.style.padding = "8px 14px";
  bubble.style.borderRadius = "12px";
  bubble.style.fontSize = "13px";
  bubble.style.alignSelf = isMine ? "flex-end" : "flex-start";
  bubble.style.background = isMine ? "var(--primary-lime)" : "rgba(255,255,255,0.12)";
  bubble.style.color = isMine ? "#121812" : "#FFF";
  bubble.style.fontWeight = isMine ? "700" : "500";
  bubble.style.marginBottom = "4px";

  const senderName = isMine ? 'You' : (msg.user_name || msg.sender || 'Teammate');
  const bodyText = msg.body || msg.message || '';

  bubble.innerHTML = `
    <div style="font-size: 10px; opacity: 0.8; margin-bottom: 2px; font-weight: 800; text-transform: uppercase;">${senderName}</div>
    <div style="word-break: break-word;">${bodyText}</div>
  `;
  el.chatMessagesBox.appendChild(bubble);
  el.chatMessagesBox.scrollTop = el.chatMessagesBox.scrollHeight;
}

if (el.chatSendForm) {
  el.chatSendForm.addEventListener("submit", (e) => {
    e.preventDefault();
    if (!state.activeChatWs || state.activeChatWs.readyState !== WebSocket.OPEN) {
      showToast("Chat connecting...", "warning");
      return;
    }
    const text = el.chatInputField.value.trim();
    if (!text) return;
    state.activeChatWs.send(JSON.stringify({ body: text, message: text }));
    el.chatInputField.value = "";
  });
}

// ====================================================================
// 10. Modals Management (Host Game, Book Turf, Rate Game)
// ====================================================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add("open");
}
function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
}
window.openModal = openModal;
window.closeModal = closeModal;

// ====================================================================
// Standard 1-Hour Time Slots Blocks (Playspots / Playo format)
// ====================================================================
const STANDARD_SLOTS = [
  { label: "06:00 - 07:00 AM", start: "06:00", end: "07:00", from: "06:00 AM", to: "07:00 AM" },
  { label: "07:00 - 08:00 AM", start: "07:00", end: "08:00", from: "07:00 AM", to: "08:00 AM" },
  { label: "08:00 - 09:00 AM", start: "08:00", end: "09:00", from: "08:00 AM", to: "09:00 AM" },
  { label: "09:00 - 10:00 AM", start: "09:00", end: "10:00", from: "09:00 AM", to: "10:00 AM" },
  { label: "10:00 - 11:00 AM", start: "10:00", end: "11:00", from: "10:00 AM", to: "11:00 AM" },
  { label: "11:00 AM - 12:00 PM", start: "11:00", end: "12:00", from: "11:00 AM", to: "12:00 PM" },
  { label: "12:00 - 01:00 PM", start: "12:00", end: "13:00", from: "12:00 PM", to: "01:00 PM" },
  { label: "01:00 - 02:00 PM", start: "13:00", end: "14:00", from: "01:00 PM", to: "02:00 PM" },
  { label: "02:00 - 03:00 PM", start: "14:00", end: "15:00", from: "02:00 PM", to: "03:00 PM" },
  { label: "03:00 - 04:00 PM", start: "15:00", end: "16:00", from: "03:00 PM", to: "04:00 PM" },
  { label: "04:00 - 05:00 PM", start: "16:00", end: "17:00", from: "04:00 PM", to: "05:00 PM" },
  { label: "05:00 - 06:00 PM", start: "17:00", end: "18:00", from: "05:00 PM", to: "06:00 PM" },
  { label: "06:00 - 07:00 PM", start: "18:00", end: "19:00", from: "06:00 PM", to: "07:00 PM" },
  { label: "07:00 - 08:00 PM", start: "19:00", end: "20:00", from: "07:00 PM", to: "08:00 PM" },
  { label: "08:00 - 09:00 PM", start: "20:00", end: "21:00", from: "08:00 PM", to: "09:00 PM" },
  { label: "09:00 - 10:00 PM", start: "21:00", end: "22:00", from: "09:00 PM", to: "10:00 PM" },
  { label: "10:00 - 11:00 PM", start: "22:00", end: "23:00", from: "10:00 PM", to: "11:00 PM" }
];

// Date Blocks Carousel Generator (Next 7 Days)
// Date Blocks Carousel Generator (Next 30 Days / Full Month)
function renderDateBlocksCarousel(containerId, hiddenInputId, onDateSelect = null) {
  const container = document.getElementById(containerId);
  const hiddenInput = document.getElementById(hiddenInputId);
  if (!container) return;

  container.innerHTML = "";
  const now = new Date();

  for (let i = 0; i < 30; i++) {
    const d = new Date(now.getTime() + i * 86400000);
    const dateNum = d.getDate();
    const dayStr = d.toLocaleDateString("en-US", { weekday: "short" }).toUpperCase();
    const monthStr = d.toLocaleDateString("en-US", { month: "short" }).toUpperCase();
    const isoDate = d.toISOString().slice(0, 10);

    const block = document.createElement("div");
    block.className = `date-block-btn ${i === 0 ? "active" : ""}`;
    block.innerHTML = `
      <span class="date-num">${dateNum}</span>
      <span class="date-day">${dayStr}</span>
      <span style="font-size: 8px; color: rgba(255,255,255,0.4); text-transform: uppercase; margin-top: 1px;">${monthStr}</span>
    `;

    if (i === 0) {
      if (hiddenInput) hiddenInput.value = isoDate;
      if (onDateSelect) onDateSelect(isoDate, d);
    }

    block.onclick = () => {
      container.querySelectorAll(".date-block-btn").forEach(b => b.classList.remove("active"));
      block.classList.add("active");
      if (hiddenInput) hiddenInput.value = isoDate;
      if (onDateSelect) onDateSelect(isoDate, d);
    };

    container.appendChild(block);
  }
}

// Available Slot Blocks Grid Generator
function renderSlotBlocksGrid(containerId, startInputId, endInputId, defaultStart = "17:00", onSelectCallback = null) {
  const container = document.getElementById(containerId);
  const startInput = document.getElementById(startInputId);
  const endInput = document.getElementById(endInputId);

  if (!container) return;
  container.innerHTML = "";

  STANDARD_SLOTS.forEach(slot => {
    const block = document.createElement("div");
    block.className = `slot-block-btn ${slot.start === defaultStart ? "active" : ""}`;
    block.textContent = slot.label;

    if (slot.start === defaultStart) {
      if (startInput) startInput.value = slot.start;
      if (endInput) endInput.value = slot.end;
      if (onSelectCallback) onSelectCallback(slot);
    }

    block.onclick = () => {
      container.querySelectorAll(".slot-block-btn").forEach(b => b.classList.remove("active"));
      block.classList.add("active");
      if (startInput) startInput.value = slot.start;
      if (endInput) endInput.value = slot.end;
      if (onSelectCallback) onSelectCallback(slot);
    };

    container.appendChild(block);
  });
}

// Modal City Change Handler (Dynamic Venue Dropdown)
async function handleModalCityChange(selectedCity, preselectedVenueId = null) {
  const venueSelect = document.getElementById("game-venue-id");
  if (!venueSelect) return;

  venueSelect.innerHTML = `<option value="">Loading venues in ${selectedCity}...</option>`;
  try {
    const venues = await api.listVenues(selectedCity);
    if (!venues || venues.length === 0) {
      venueSelect.innerHTML = `<option value="">No registered venues in ${selectedCity} (Street/Open ground)</option>`;
    } else {
      venueSelect.innerHTML = `<option value="">No Arena / Street pickup</option>` + 
        venues.map(v => `<option value="${v.id}" ${preselectedVenueId === v.id ? 'selected' : ''}>🏟️ ${v.name} (₹${v.hourly_rate}/hr)</option>`).join("");
      if (preselectedVenueId) venueSelect.value = preselectedVenueId;
    }
  } catch (err) {
    venueSelect.innerHTML = `<option value="">No Arena / Street pickup</option>`;
  }
}
window.handleModalCityChange = handleModalCityChange;

// Host Game Modal
function openHostGameModal(preselectedVenueId = null) {
  const citySelect = document.getElementById("game-city");
  const targetCity = state.selectedCity || "Bangalore";
  if (citySelect) {
    citySelect.value = targetCity;
  }

  // Populate dynamic venues for the selected city
  handleModalCityChange(targetCity, preselectedVenueId);

  // Render Date Blocks Carousel (Next 7 days)
  renderDateBlocksCarousel("game-date-carousel", "game-date");

  // Render Available Slot Blocks
  const now = new Date();
  now.setMinutes(0, 0, 0);
  now.setHours(now.getHours() + 1);
  const nextHourStr = `${String(now.getHours()).padStart(2, '0')}:00`;
  const defaultSlotStart = (now.getHours() >= 6 && now.getHours() <= 22) ? nextHourStr : "17:00";

  renderSlotBlocksGrid("game-slot-grid", "game-start-time", "game-end-time", defaultSlotStart);

  openModal("modal-create-game");
}
window.openHostGameModal = openHostGameModal;

const createGameForm = document.getElementById("create-game-form");
if (createGameForm) {
  createGameForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const sport = document.getElementById("game-sport").value;
    const city = document.getElementById("game-city").value;
    const maxPlayers = parseInt(document.getElementById("game-max-players").value, 10);
    const dateVal = document.getElementById("game-date")?.value;
    const startTimeVal = document.getElementById("game-start-time")?.value;
    const skillLevel = document.getElementById("game-skill-level")?.value || "All Levels";
    const venueId = document.getElementById("game-venue-id").value || null;

    let startsAt = null;
    if (dateVal && startTimeVal) {
      startsAt = new Date(`${dateVal}T${startTimeVal}:00`).toISOString();
    }

    try {
      showToast("Launching match lobby...");
      await api.createGame(sport, city, maxPlayers, startsAt, skillLevel, venueId);
      showToast("Match lobby launched successfully!");
      closeModal("modal-create-game");
      loadGames();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

let activeVenueHourlyRate = 1500;

// Book Venue Modal
function openBookVenueModal(venueId, venueName, hourlyRate) {
  activeVenueHourlyRate = hourlyRate || 1500;
  const idInput = document.getElementById("book-venue-id");
  const nameEl = document.getElementById("book-venue-name");
  const rateEl = document.getElementById("book-venue-rate");

  if (idInput) idInput.value = venueId;
  if (nameEl) nameEl.textContent = `Book ${venueName}`;
  if (rateEl) rateEl.textContent = `₹${hourlyRate} / hour`;

  const totalAmountEl = document.getElementById("book-total-amount");
  const headerDateEl = document.getElementById("book-summary-date-header");
  const fromEl = document.getElementById("book-summary-from");
  const toEl = document.getElementById("book-summary-to");

  if (totalAmountEl) totalAmountEl.textContent = `₹${activeVenueHourlyRate.toLocaleString()}`;

  // 1. Render Date Blocks Strip
  renderDateBlocksCarousel("book-date-carousel", "book-date", (isoDate, dt) => {
    if (headerDateEl) {
      headerDateEl.textContent = dt.toLocaleDateString("en-US", { weekday: "short", day: "2-digit", month: "long", year: "numeric" });
    }
  });

  // 2. Render Slot Blocks Grid
  const now = new Date();
  now.setMinutes(0, 0, 0);
  now.setHours(now.getHours() + 1);
  const nextHourStr = `${String(now.getHours()).padStart(2, '0')}:00`;
  const defaultSlotStart = (now.getHours() >= 6 && now.getHours() <= 22) ? nextHourStr : "17:00";

  renderSlotBlocksGrid("book-slot-grid", "book-start-time", "book-end-time", defaultSlotStart, (slot) => {
    if (fromEl) fromEl.textContent = slot.from;
    if (toEl) toEl.textContent = slot.to;
    if (totalAmountEl) totalAmountEl.textContent = `₹${activeVenueHourlyRate.toLocaleString()}`;
  });

  openModal("modal-book-venue");
}
window.openBookVenueModal = openBookVenueModal;

const bookVenueForm = document.getElementById("book-venue-form");
if (bookVenueForm) {
  bookVenueForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const venueId = document.getElementById("book-venue-id").value;
    const dateVal = document.getElementById("book-date")?.value;
    const startTimeVal = document.getElementById("book-start-time")?.value;
    const endTimeVal = document.getElementById("book-end-time")?.value;

    if (!dateVal || !startTimeVal || !endTimeVal) {
      showToast("Please select a date and time slot.", "error");
      return;
    }

    const startTime = new Date(`${dateVal}T${startTimeVal}:00`).toISOString();
    const endTime = new Date(`${dateVal}T${endTimeVal}:00`).toISOString();

    try {
      showToast("Locking court slot...");
      const booking = await api.createBooking(venueId, startTime, endTime);
      showToast("Slot locked! Processing checkout...");
      closeModal("modal-book-venue");
      await handlePayBooking(booking.id);
      loadMyBookings();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// Pay Booking Handler
async function handlePayBooking(bookingId) {
  try {
    const order = await api.payBooking(bookingId);
    showToast(`Order created (₹${order.amount}). Confirming payment...`);
    
    await api.processWebhook({
      event: "payment.captured",
      payload: {
        payment: {
          entity: {
            id: `pay_${Date.now()}`,
            order_id: order.id,
            status: "captured",
            notes: { booking_id: bookingId }
          }
        }
      }
    });

    showToast("Payment captured & Court slot confirmed!", "success");
    loadMyBookings();
  } catch (err) {
    showToast(`Checkout note: ${err.message}`, "warning");
    loadMyBookings();
  }
}
window.handlePayBooking = handlePayBooking;

// Cancel Booking Handler
async function handleCancelBooking(bookingId) {
  try {
    await api.cancelBooking(bookingId);
    showToast("Booking cancelled successfully.");
    loadMyBookings();
  } catch (err) {
    showToast(err.message, "error");
  }
}
window.handleCancelBooking = handleCancelBooking;

// Register Venue Modal
function openCreateVenueModal() {
  openModal("modal-create-venue");
}
window.openCreateVenueModal = openCreateVenueModal;

const createVenueForm = document.getElementById("create-venue-form");
if (createVenueForm) {
  createVenueForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("venue-name").value;
    const address = document.getElementById("venue-address").value;
    const city = document.getElementById("venue-city").value;
    const sportsStr = document.getElementById("venue-sports").value;
    const rate = parseFloat(document.getElementById("venue-rate").value);

    const sports = sportsStr.split(",").map(s => s.trim()).filter(s => s);

    try {
      await api.createVenue({
        name,
        address,
        city,
        sports,
        hourly_rate: rate,
        opening_time: "06:00",
        closing_time: "23:00",
        lat: 19.0760,
        lng: 72.8777
      });
      showToast("Court arena registered!");
      closeModal("modal-create-venue");
      loadVenues();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// Create Team Modal
function openCreateTeamModal() {
  openModal("modal-create-team");
}
window.openCreateTeamModal = openCreateTeamModal;

const createTeamForm = document.getElementById("create-team-form");
if (createTeamForm) {
  createTeamForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = document.getElementById("team-name").value;
    const description = document.getElementById("team-desc").value;

    try {
      await api.createTeam(name, description);
      showToast("Sports club registered!");
      closeModal("modal-create-team");
      loadTeams();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

// Init
window.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
});
