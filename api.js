const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API_BASE = isLocal 
  ? "http://127.0.0.1:8001" 
  : (window.SQUADUP_API_BASE || "https://squadup-api-6rl8.onrender.com");

const WS_BASE = isLocal
  ? "ws://127.0.0.1:8001"
  : (window.SQUADUP_WS_BASE || "wss://squadup-api-6rl8.onrender.com");

const api = {
  // Token Management
  getToken() {
    return localStorage.getItem("turf_token");
  },
  
  setToken(token) {
    if (token) {
      localStorage.setItem("turf_token", token);
    } else {
      localStorage.removeItem("turf_token");
    }
  },

  getUser() {
    const userStr = localStorage.getItem("turf_user");
    return userStr ? JSON.parse(userStr) : null;
  },

  setUser(user) {
    if (user) {
      localStorage.setItem("turf_user", JSON.stringify(user));
    } else {
      localStorage.removeItem("turf_user");
    }
  },

  // HTTP Requests helper
  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    
    // Default headers
    const headers = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    // Attach auth token if available
    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);
      
      // Handle No Content (204)
      if (response.status === 204) {
        return null;
      }

      let data;
      try {
        data = await response.json();
      } catch (e) {
        data = { detail: response.statusText || `Request failed with status ${response.status}` };
      }
      
      if (!response.ok) {
        // If token expired or invalid, clear token
        if (response.status === 401) {
          this.setToken(null);
          this.setUser(null);
          window.dispatchEvent(new Event("auth-changed"));
        }
        const errorMsg = Array.isArray(data.detail) ? data.detail.map(d => d.msg).join(", ") : (data.detail || "API Request failed");
        throw new Error(errorMsg);
      }
      
      return data;
    } catch (error) {
      console.error(`API Error on ${endpoint}:`, error);
      throw error;
    }
  },

  // Auth & Users
  async login(email, password) {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const url = `${API_BASE}/auth/jwt/login`;
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Login failed");
    }

    this.setToken(data.access_token);
    
    // Fetch user details immediately to save profile cache
    const user = await this.getCurrentUser();
    this.setUser(user);
    window.dispatchEvent(new Event("auth-changed"));
    return { token: data.access_token, user };
  },

  async register(email, password, name, skillLevel, city) {
    const data = await this.request("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        name,
        skill_level: skillLevel,
        city,
      }),
    });
    return data;
  },

  async getCurrentUser() {
    return await this.request("/users/me");
  },

  async updateProfile(profileData) {
    const user = await this.request("/users/me", {
      method: "PATCH",
      body: JSON.stringify(profileData),
    });
    this.setUser(user);
    window.dispatchEvent(new Event("auth-changed"));
    return user;
  },

  logout() {
    this.setToken(null);
    this.setUser(null);
    window.dispatchEvent(new Event("auth-changed"));
  },

  // Games
  async listGames(filters = {}) {
    const params = new URLSearchParams();
    Object.keys(filters).forEach((key) => {
      if (filters[key] !== undefined && filters[key] !== null && filters[key] !== "") {
        params.append(key, filters[key]);
      }
    });
    const query = params.toString() ? `?${params.toString()}` : "";
    return await this.request(`/games${query}`);
  },

  async getGame(gameId) {
    return await this.request(`/games/${gameId}`);
  },

  async createGame(sport, city, maxPlayers, startsAt = null, skillLevel = "All Levels", venueId = null, teamId = null) {
    return await this.request("/games", {
      method: "POST",
      body: JSON.stringify({
        sport,
        city,
        max_players: maxPlayers,
        starts_at: startsAt || null,
        skill_level: skillLevel || "All Levels",
        venue_id: venueId || null,
        team_id: teamId || null,
      }),
    });
  },

  async joinGame(gameId) {
    return await this.request(`/games/${gameId}/join`, {
      method: "POST",
    });
  },

  async leaveGame(gameId) {
    return await this.request(`/games/${gameId}/leave`, {
      method: "POST",
    });
  },

  async cancelGame(gameId) {
    return await this.request(`/games/${gameId}`, {
      method: "DELETE",
    });
  },

  async completeGame(gameId) {
    return await this.request(`/games/${gameId}/complete`, {
      method: "POST",
    });
  },

  // Ratings
  async submitRating(gameId, ratedUserId, score, comment = "") {
    return await this.request(`/games/${gameId}/ratings`, {
      method: "POST",
      body: JSON.stringify({
        rated_id: ratedUserId,
        score: parseInt(score, 10),
        comment: comment || null,
      }),
    });
  },

  // Venues
  async listVenues(city = null, sport = null) {
    const params = new URLSearchParams();
    if (city) params.append("city", city);
    if (sport) params.append("sport", sport);
    const query = params.toString() ? `?${params.toString()}` : "";
    return await this.request(`/venues${query}`);
  },

  async getVenue(venueId) {
    return await this.request(`/venues/${venueId}`);
  },

  async createVenue(venueData) {
    return await this.request("/venues", {
      method: "POST",
      body: JSON.stringify(venueData),
    });
  },

  // Bookings
  async listBookings() {
    return await this.request("/bookings");
  },

  async createBooking(venueId, startsAt, endsAt) {
    return await this.request("/bookings", {
      method: "POST",
      body: JSON.stringify({
        venue_id: venueId,
        starts_at: startsAt,
        ends_at: endsAt,
      }),
    });
  },

  async cancelBooking(bookingId) {
    return await this.request(`/bookings/${bookingId}/cancel`, {
      method: "POST",
    });
  },

  // Payments
  async payBooking(bookingId) {
    return await this.request(`/bookings/${bookingId}/pay`, {
      method: "POST",
    });
  },

  async processWebhook(paymentPayload) {
    return await this.request("/payments/webhook", {
      method: "POST",
      body: JSON.stringify(paymentPayload),
    });
  },

  // Notifications
  async listNotifications() {
    return await this.request("/notifications");
  },

  async markNotificationRead(notificationId) {
    return await this.request(`/notifications/${notificationId}/read`, {
      method: "POST",
    });
  },

  async registerDeviceToken(token, platform = "web") {
    return await this.request("/notifications/tokens", {
      method: "POST",
      body: JSON.stringify({
        token,
        platform,
      }),
    });
  },

  // Teams
  async listTeams() {
    return await this.request("/teams");
  },

  async getTeam(teamId) {
    return await this.request(`/teams/${teamId}`);
  },

  async createTeam(name, description = "") {
    return await this.request("/teams", {
      method: "POST",
      body: JSON.stringify({
        name,
        description: description || null,
      }),
    });
  },

  async joinTeam(teamId) {
    return await this.request(`/teams/${teamId}/join`, {
      method: "POST",
    });
  },

  async updateMemberRole(teamId, userId, role) {
    return await this.request(`/teams/${teamId}/members/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  },

  // Social
  async followUser(userId) {
    return await this.request(`/users/${userId}/follow`, {
      method: "POST",
    });
  },

  async unfollowUser(userId) {
    return await this.request(`/users/${userId}/unfollow`, {
      method: "POST",
    });
  },

  async getFollowFeed() {
    return await this.request("/users/me/feed");
  },

  async getFollowers(userId) {
    return await this.request(`/users/${userId}/followers`);
  },

  async getFollowing(userId) {
    return await this.request(`/users/${userId}/following`);
  },

  async listUsers(city = null) {
    const params = city ? `?city=${encodeURIComponent(city)}` : "";
    return await this.request(`/users${params}`);
  },

  async completeGame(gameId) {
    return await this.request(`/games/${gameId}/complete`, {
      method: "POST",
    });
  },

  async ratePlayer(gameId, ratedId, score, comment = "") {
    return await this.request(`/games/${gameId}/ratings`, {
      method: "POST",
      body: JSON.stringify({
        rated_id: ratedId,
        score: parseInt(score, 10),
        comment: comment || null
      })
    });
  },

  async submitRating(gameId, ratedId, score, comment = "") {
    return await this.ratePlayer(gameId, ratedId, score, comment);
  },

  async unfollowUser(userId) {
    return await this.request(`/users/${userId}/unfollow`, {
      method: "POST",
    });
  },

  async updateProfile(data) {
    return await this.request("/users/me", {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  getChatWebSocketUrl(gameId) {
    const token = this.getToken();
    return `${WS_BASE}/ws/games/${gameId}/chat?token=${token}`;
  }
};

window.api = api;
export default api;
