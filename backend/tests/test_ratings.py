import pytest
from httpx import AsyncClient

async def get_user_info_and_headers(
    client: AsyncClient,
    email: str,
    password: str,
    name: str = "Test User",
    skill_level: str = "Beginner",
    city: str = "Mumbai"
) -> tuple[dict, dict]:
    # Helper to register and login a user, returning (user_info, auth_headers)
    reg_data = {
        "email": email,
        "password": password,
        "name": name,
        "skill_level": skill_level,
        "city": city
    }
    reg_response = await client.post("/auth/register", json=reg_data)
    user_info = reg_response.json()
    
    login_data = {
        "username": email,
        "password": password
    }
    login_response = await client.post("/auth/jwt/login", data=login_data)
    token = login_response.json()["access_token"]
    return user_info, {"Authorization": f"Bearer {token}"}

async def test_complete_game(client: AsyncClient):
    # Register host and player
    host_info, host_headers = await get_user_info_and_headers(client, "host1@example.com", "pass123")
    player_info, player_headers = await get_user_info_and_headers(client, "player1_1@example.com", "pass123")
    
    # Create game
    game_res = await client.post(
        "/games",
        json={"sport": "Cricket", "city": "Mumbai", "max_players": 2},
        headers=host_headers
    )
    assert game_res.status_code == 201
    game_id = game_res.json()["id"]
    
    # Player joins
    join_res = await client.post(f"/games/{game_id}/join", headers=player_headers)
    assert join_res.status_code == 200
    
    # Non-host attempts to complete the game
    complete_fail = await client.post(f"/games/{game_id}/complete", headers=player_headers)
    assert complete_fail.status_code == 403
    assert complete_fail.json()["detail"] == "Only the host can complete this game"
    
    # Host completes the game
    complete_success = await client.post(f"/games/{game_id}/complete", headers=host_headers)
    assert complete_success.status_code == 200
    assert complete_success.json()["status"] == "completed"

async def test_rating_validations(client: AsyncClient):
    # Register users
    host_info, host_headers = await get_user_info_and_headers(client, "host2@example.com", "pass123")
    player_info, player_headers = await get_user_info_and_headers(client, "player2_1@example.com", "pass123")
    outsider_info, outsider_headers = await get_user_info_and_headers(client, "outsider@example.com", "pass123")
    
    # Create game
    game_res = await client.post(
        "/games",
        json={"sport": "Football", "city": "Mumbai", "max_players": 2},
        headers=host_headers
    )
    game_id = game_res.json()["id"]
    
    # Player joins
    await client.post(f"/games/{game_id}/join", headers=player_headers)
    
    # 1. Attempt to rate before game is completed
    rate_fail_not_completed = await client.post(
        f"/games/{game_id}/ratings",
        json={"rated_id": player_info["id"], "score": 5},
        headers=host_headers
    )
    assert rate_fail_not_completed.status_code == 400
    assert "incomplete game" in rate_fail_not_completed.json()["detail"]
    
    # Complete the game
    await client.post(f"/games/{game_id}/complete", headers=host_headers)
    
    # 2. Attempt self-rating
    rate_fail_self = await client.post(
        f"/games/{game_id}/ratings",
        json={"rated_id": host_info["id"], "score": 5},
        headers=host_headers
    )
    assert rate_fail_self.status_code == 400
    assert "cannot rate yourself" in rate_fail_self.json()["detail"]
    
    # 3. Attempt to rate when rater is not in the game
    rate_fail_rater_not_in_game = await client.post(
        f"/games/{game_id}/ratings",
        json={"rated_id": player_info["id"], "score": 5},
        headers=outsider_headers
    )
    assert rate_fail_rater_not_in_game.status_code == 400
    assert "Rater must be a player" in rate_fail_rater_not_in_game.json()["detail"]
    
    # 4. Attempt to rate when rated is not in the game
    rate_fail_rated_not_in_game = await client.post(
        f"/games/{game_id}/ratings",
        json={"rated_id": outsider_info["id"], "score": 5},
        headers=host_headers
    )
    assert rate_fail_rated_not_in_game.status_code == 400
    assert "Rated user must be a player" in rate_fail_rated_not_in_game.json()["detail"]
    
    # 5. Invalid score bounds (0 or 6)
    rate_fail_bounds_low = await client.post(
        f"/games/{game_id}/ratings",
        json={"rated_id": player_info["id"], "score": 0},
        headers=host_headers
    )
    assert rate_fail_bounds_low.status_code == 422
    
    rate_fail_bounds_high = await client.post(
        f"/games/{game_id}/ratings",
        json={"rated_id": player_info["id"], "score": 6},
        headers=host_headers
    )
    assert rate_fail_bounds_high.status_code == 422

async def test_karma_aggregation_and_duplicates(client: AsyncClient):
    # Register players
    host_info, host_headers = await get_user_info_and_headers(client, "host3@example.com", "pass123")
    player_info, player_headers = await get_user_info_and_headers(client, "player3_1@example.com", "pass123")
    player2_info, player2_headers = await get_user_info_and_headers(client, "player3_2@example.com", "pass123")
    
    # Assert initial karma is 5.0
    p1_profile = await client.get("/users/me", headers=player_headers)
    assert p1_profile.json()["karma"] == 5.0
    
    # Create game 1 (max 3 players)
    game_res1 = await client.post(
        "/games",
        json={"sport": "Tennis", "city": "Mumbai", "max_players": 3},
        headers=host_headers
    )
    game_id1 = game_res1.json()["id"]
    
    # Join both players
    await client.post(f"/games/{game_id1}/join", headers=player_headers)
    await client.post(f"/games/{game_id1}/join", headers=player2_headers)
    
    # Complete game 1
    await client.post(f"/games/{game_id1}/complete", headers=host_headers)
    
    # Host rates Player 1 with a score of 4
    rate_res1 = await client.post(
        f"/games/{game_id1}/ratings",
        json={"rated_id": player_info["id"], "score": 4, "comment": "Great teammate!"},
        headers=host_headers
    )
    assert rate_res1.status_code == 201
    assert rate_res1.json()["score"] == 4
    assert rate_res1.json()["comment"] == "Great teammate!"
    
    # Assert Player 1's karma is updated to 4.0
    p1_profile = await client.get("/users/me", headers=player_headers)
    assert p1_profile.json()["karma"] == 4.0
    
    # Try to rate duplicate
    rate_dup = await client.post(
        f"/games/{game_id1}/ratings",
        json={"rated_id": player_info["id"], "score": 5},
        headers=host_headers
    )
    assert rate_dup.status_code == 409
    assert "already rated" in rate_dup.json()["detail"]
    
    # Create game 2 (max 3 players)
    game_res2 = await client.post(
        "/games",
        json={"sport": "Tennis", "city": "Mumbai", "max_players": 3},
        headers=host_headers
    )
    game_id2 = game_res2.json()["id"]
    
    # Join players to game 2
    await client.post(f"/games/{game_id2}/join", headers=player_headers)
    await client.post(f"/games/{game_id2}/join", headers=player2_headers)
    
    # Complete game 2
    await client.post(f"/games/{game_id2}/complete", headers=host_headers)
    
    # Host rates Player 1 with a score of 2
    rate_res2 = await client.post(
        f"/games/{game_id2}/ratings",
        json={"rated_id": player_info["id"], "score": 2, "comment": "Okayish"},
        headers=host_headers
    )
    assert rate_res2.status_code == 201
    
    # Karma should be (4 + 2) / 2 = 3.0
    p1_profile = await client.get("/users/me", headers=player_headers)
    assert p1_profile.json()["karma"] == 3.0
    
    # Player 2 rates Player 1 with a score of 3 in game 2
    rate_res3 = await client.post(
        f"/games/{game_id2}/ratings",
        json={"rated_id": player_info["id"], "score": 3},
        headers=player2_headers
    )
    assert rate_res3.status_code == 201
    
    # Karma should be (4 + 2 + 3) / 3 = 3.0
    p1_profile = await client.get("/users/me", headers=player_headers)
    assert p1_profile.json()["karma"] == 3.0
    
    # Player 2 rates Player 1 with a score of 6 (out of bounds)
    rate_res4 = await client.post(
        f"/games/{game_id2}/ratings",
        json={"rated_id": player_info["id"], "score": 5},
        headers=player2_headers
    )
    # Already rated this player in this game
    assert rate_res4.status_code == 409
