import pytest
import uuid
from httpx import AsyncClient

async def get_user_info_and_headers(
    client: AsyncClient,
    email: str,
    password: str,
    name: str = "Test User"
) -> tuple[dict, dict]:
    reg_data = {
        "email": email,
        "password": password,
        "name": name,
        "skill_level": "Intermediate",
        "city": "Mumbai"
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


async def test_team_creation_and_uniqueness(client: AsyncClient):
    user_info, headers = await get_user_info_and_headers(client, "captain@example.com", "pass123", "Captain A")
    
    # Create Team
    team_data = {
        "name": "Mumbai Warriors",
        "description": "The local champions"
    }
    res = await client.post("/teams", json=team_data, headers=headers)
    assert res.status_code == 201
    team = res.json()
    assert team["name"] == "Mumbai Warriors"
    assert team["description"] == "The local champions"
    assert "id" in team
    assert "created_at" in team
    
    # Check that creator is captain
    detail_res = await client.get(f"/teams/{team['id']}", headers=headers)
    assert detail_res.status_code == 200
    details = detail_res.json()
    assert len(details["members"]) == 1
    assert details["members"][0]["user_id"] == user_info["id"]
    assert details["members"][0]["name"] == "Captain A"
    assert details["members"][0]["role"] == "captain"
    
    # Attempt to create team with duplicate name
    res_dup = await client.post("/teams", json=team_data, headers=headers)
    assert res_dup.status_code == 400
    assert "already taken" in res_dup.json()["detail"]


async def test_list_and_retrieve_teams(client: AsyncClient):
    _, headers = await get_user_info_and_headers(client, "user_list@example.com", "pass123")
    
    # Create multiple teams
    await client.post("/teams", json={"name": "Team One"}, headers=headers)
    await client.post("/teams", json={"name": "Team Two"}, headers=headers)
    
    # List teams
    res = await client.get("/teams", headers=headers)
    assert res.status_code == 200
    teams = res.json()
    assert len(teams) >= 2
    
    # Test pagination
    res_pag = await client.get("/teams?limit=1&offset=0", headers=headers)
    assert res_pag.status_code == 200
    assert len(res_pag.json()) == 1


async def test_join_and_leave_lifecycle(client: AsyncClient):
    user_a, headers_a = await get_user_info_and_headers(client, "user_a@example.com", "pass123", "User A")
    user_b, headers_b = await get_user_info_and_headers(client, "user_b@example.com", "pass123", "User B")
    
    # User A creates a team
    res_create = await client.post("/teams", json={"name": "Solos Team"}, headers=headers_a)
    team = res_create.json()
    team_id = team["id"]
    
    # User B joins
    res_join = await client.post(f"/teams/{team_id}/join", headers=headers_b)
    assert res_join.status_code == 200
    
    # User B tries to join again
    res_join_dup = await client.post(f"/teams/{team_id}/join", headers=headers_b)
    assert res_join_dup.status_code == 400
    
    # Check members in team details
    res_details = await client.get(f"/teams/{team_id}", headers=headers_a)
    details = res_details.json()
    assert len(details["members"]) == 2
    
    # Captain (User A) tries to leave
    res_leave_cap = await client.post(f"/teams/{team_id}/leave", headers=headers_a)
    assert res_leave_cap.status_code == 400
    assert "Captain cannot leave" in res_leave_cap.json()["detail"]
    
    # User B leaves
    res_leave_b = await client.post(f"/teams/{team_id}/leave", headers=headers_b)
    assert res_leave_b.status_code == 200
    
    # User B leaves again (should fail because no longer a member)
    res_leave_b_again = await client.post(f"/teams/{team_id}/leave", headers=headers_b)
    assert res_leave_b_again.status_code == 400
    
    # Captain leaves (now that they are the only member, team should be deleted)
    res_leave_cap_ok = await client.post(f"/teams/{team_id}/leave", headers=headers_a)
    assert res_leave_cap_ok.status_code == 200
    
    # Verify team is deleted
    res_get_deleted = await client.get(f"/teams/{team_id}", headers=headers_a)
    assert res_get_deleted.status_code == 404


async def test_role_updates_and_captaincy_transfers(client: AsyncClient):
    user_a, headers_a = await get_user_info_and_headers(client, "cap_a@example.com", "pass123", "User A")
    user_b, headers_b = await get_user_info_and_headers(client, "cap_b@example.com", "pass123", "User B")
    
    # User A creates a team
    res_create = await client.post("/teams", json={"name": "Role Test Team"}, headers=headers_a)
    team = res_create.json()
    team_id = team["id"]
    
    # User B joins
    await client.post(f"/teams/{team_id}/join", headers=headers_b)
    
    # Non-captain (User B) tries to update roles
    res_b_update = await client.post(
        f"/teams/{team_id}/members/{user_a['id']}/role",
        json={"role": "member"},
        headers=headers_b
    )
    assert res_b_update.status_code == 403
    
    # Captain (User A) tries to update own role
    res_self_update = await client.post(
        f"/teams/{team_id}/members/{user_a['id']}/role",
        json={"role": "member"},
        headers=headers_a
    )
    assert res_self_update.status_code == 400
    
    # Captain (User A) promotes B to captain
    res_promote = await client.post(
        f"/teams/{team_id}/members/{user_b['id']}/role",
        json={"role": "captain"},
        headers=headers_a
    )
    assert res_promote.status_code == 200
    
    # Get details, verify roles are swapped
    res_details = await client.get(f"/teams/{team_id}", headers=headers_b)
    members = res_details.json()["members"]
    roles_map = {m["user_id"]: m["role"] for m in members}
    assert roles_map[user_a["id"]] == "member"
    assert roles_map[user_b["id"]] == "captain"
    
    # Demoted User A tries to change roles (should be forbidden now)
    res_demoted_update = await client.post(
        f"/teams/{team_id}/members/{user_b['id']}/role",
        json={"role": "member"},
        headers=headers_a
    )
    assert res_demoted_update.status_code == 403


async def test_team_games_hosting_and_filtering(client: AsyncClient):
    user_a, headers_a = await get_user_info_and_headers(client, "game_a@example.com", "pass123", "User A")
    user_b, headers_b = await get_user_info_and_headers(client, "game_b@example.com", "pass123", "User B")
    
    # Create Team
    res_team = await client.post("/teams", json={"name": "FC Pune"}, headers=headers_a)
    team = res_team.json()
    team_id = team["id"]
    
    # Create game for team as member (User A)
    res_game = await client.post(
        "/games",
        json={
            "sport": "Football",
            "city": "Pune",
            "max_players": 11,
            "team_id": team_id
        },
        headers=headers_a
    )
    assert res_game.status_code == 201
    assert res_game.json()["team_id"] == team_id
    game_id = res_game.json()["id"]
    
    # Try to create game for team as non-member (User B)
    res_game_fail = await client.post(
        "/games",
        json={
            "sport": "Football",
            "city": "Pune",
            "max_players": 11,
            "team_id": team_id
        },
        headers=headers_b
    )
    assert res_game_fail.status_code == 403
    
    # List games and filter by team_id
    res_list_filter = await client.get(f"/games?team_id={team_id}", headers=headers_a)
    assert res_list_filter.status_code == 200
    games_filtered = res_list_filter.json()
    assert len(games_filtered) == 1
    assert games_filtered[0]["id"] == game_id
    
    # Try filtering by non-existent team ID
    res_list_empty = await client.get(f"/games?team_id={uuid.uuid4()}", headers=headers_a)
    assert res_list_empty.status_code == 200
    assert len(res_list_empty.json()) == 0
