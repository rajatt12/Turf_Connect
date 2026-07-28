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


async def test_follow_and_unfollow_validation(client: AsyncClient):
    user_a, headers_a = await get_user_info_and_headers(client, "usera@example.com", "pass123", "User A")
    user_b, headers_b = await get_user_info_and_headers(client, "userb@example.com", "pass123", "User B")
    
    # Self-follow (should fail)
    res_self = await client.post(f"/users/{user_a['id']}/follow", headers=headers_a)
    assert res_self.status_code == 400
    assert "Cannot follow yourself" in res_self.json()["detail"]
    
    # Follow User B
    res_follow = await client.post(f"/users/{user_b['id']}/follow", headers=headers_a)
    assert res_follow.status_code == 200
    assert "Followed user successfully" in res_follow.json()["message"]
    
    # Duplicate follow (should fail)
    res_dup = await client.post(f"/users/{user_b['id']}/follow", headers=headers_a)
    assert res_dup.status_code == 400
    assert "Already following" in res_dup.json()["detail"]
    
    # Unfollow User B
    res_unfollow = await client.post(f"/users/{user_b['id']}/unfollow", headers=headers_a)
    assert res_unfollow.status_code == 200
    assert "Unfollowed user successfully" in res_unfollow.json()["message"]
    
    # Unfollow again (should fail)
    res_unfollow_again = await client.post(f"/users/{user_b['id']}/unfollow", headers=headers_a)
    assert res_unfollow_again.status_code == 400
    assert "Not following" in res_unfollow_again.json()["detail"]


async def test_following_and_followers_lists(client: AsyncClient):
    user_a, headers_a = await get_user_info_and_headers(client, "list_a@example.com", "pass123", "User A")
    user_b, headers_b = await get_user_info_and_headers(client, "list_b@example.com", "pass123", "User B")
    user_c, _ = await get_user_info_and_headers(client, "list_c@example.com", "pass123", "User C")
    
    # User A follows B and C
    await client.post(f"/users/{user_b['id']}/follow", headers=headers_a)
    await client.post(f"/users/{user_c['id']}/follow", headers=headers_a)
    
    # Get User A's following list
    res_following = await client.get(f"/users/{user_a['id']}/following", headers=headers_a)
    assert res_following.status_code == 200
    following = res_following.json()
    assert len(following) == 2
    following_ids = [u["id"] for u in following]
    assert user_b["id"] in following_ids
    assert user_c["id"] in following_ids
    
    # Test pagination on following
    res_following_pag = await client.get(f"/users/{user_a['id']}/following?limit=1", headers=headers_a)
    assert len(res_following_pag.json()) == 1
    
    # Get User B's followers list
    res_followers = await client.get(f"/users/{user_b['id']}/followers", headers=headers_b)
    assert res_followers.status_code == 200
    followers = res_followers.json()
    assert len(followers) == 1
    assert followers[0]["id"] == user_a["id"]


async def test_personalized_games_feed(client: AsyncClient):
    user_a, headers_a = await get_user_info_and_headers(client, "feed_a@example.com", "pass123", "User A")
    user_b, headers_b = await get_user_info_and_headers(client, "feed_b@example.com", "pass123", "User B")
    user_c, headers_c = await get_user_info_and_headers(client, "feed_c@example.com", "pass123", "User C")
    
    # Initially feed is empty
    res_feed_init = await client.get("/users/me/feed", headers=headers_a)
    assert res_feed_init.status_code == 200
    assert len(res_feed_init.json()) == 0
    
    # User A follows User B
    await client.post(f"/users/{user_b['id']}/follow", headers=headers_a)
    
    # User B creates a game (should appear in feed)
    res_game_b = await client.post(
        "/games",
        json={"sport": "Cricket", "city": "Mumbai", "max_players": 11},
        headers=headers_b
    )
    assert res_game_b.status_code == 201
    game_b_id = res_game_b.json()["id"]
    
    # User C creates a game (should NOT appear in A's feed)
    await client.post(
        "/games",
        json={"sport": "Tennis", "city": "Mumbai", "max_players": 2},
        headers=headers_c
    )
    
    # Get User A's feed
    res_feed = await client.get("/users/me/feed", headers=headers_a)
    assert res_feed.status_code == 200
    feed = res_feed.json()
    assert len(feed) == 1
    assert feed[0]["id"] == game_b_id
    assert feed[0]["sport"] == "Cricket"
    
    # User A unfollows User B
    await client.post(f"/users/{user_b['id']}/unfollow", headers=headers_a)
    
    # Feed should be empty again
    res_feed_empty = await client.get("/users/me/feed", headers=headers_a)
    assert len(res_feed_empty.json()) == 0
