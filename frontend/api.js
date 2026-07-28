/**
 * Turf API Client
 * Wraps interactions with the FastAPI backend at http://localhost:8000
 */

const API_BASE = "http://localhost:8001";
const WS_BASE = "ws://localhost:8001";

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

      const data = await response.json();
      
      if (!response.ok) {
        // If token expired or invalid, clear token
        if (response.status === 401) {
          this.setToken(null);
          this.setUser(null);
          window.dispatchEvent(new Event("auth-changed"));
        }
        throw new Error(data.detail || "API Request failed");
      }
      
      return data;
    } catch (error) {
      console.error(`API Error on ${endpoint}:`, error);
      throw error;
    }
  },

  // Auth & Users
  async login(email, password) {
    // fastapi-users expects urlencoded form body for token request
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

  async createGame(sport, city, maxPlayers, venueId = null, teamId = null) {
    return await this.request("/games", {
      method: "POST",
      body: JSON.stringify({
        sport,
        city,
        max_players: maxPlayers,
        venue_id: venueId,
        team_id: teamId,
      }),
    });
  },

  async joinGame(gameId) {
    return await this.request(`/games/${gameId}/join`, {
      method: "POST",
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

  async listGamesAtVenue(venueId) {
    return await this.request(`/venues/${venueId}/games`);
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
  async createPayment(bookingId, amount) {
    return await this.request("/payments/order", {
      method: "POST",
      body: JSON.stringify({
        booking_id: bookingId,
        amount,
      }),
    });
  },

  async verifyPayment(paymentPayload) {
    return await this.request("/payments/webhook", {
      method: "POST",
      body: JSON.stringify(paymentPayload),
    });
  },

  getChatWebSocketUrl(gameId) {
    const token = this.getToken();
    return `${WS_BASE}/ws/games/${gameId}/chat?token=${token}`;
  },

  // Ratings
  async rateUser(gameId, ratedUserId, score, comment = "") {
    return await this.request(`/ratings/${gameId}`, {
      method: "POST",
      body: JSON.stringify({
        rated_id: ratedUserId,
        score,
        comment,
      }),
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
    return await this.request("/notifications/devices", {
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
        description,
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
    return await this.request(`/social/follow/${userId}`, {
      method: "POST",
    });
  },

  async unfollowUser(userId) {
    return await this.request(`/social/unfollow/${userId}`, {
      method: "POST",
    });
  },

  async getFollowFeed() {
    return await this.request("/social/feed");
  }
};

window.api = api; // Make it available globally
export default api;
