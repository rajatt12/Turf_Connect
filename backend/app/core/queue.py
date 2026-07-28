import json
import uuid
import asyncio
import random
from typing import Optional, Any
import redis.asyncio as redis
from sqlmodel import select

from app.core.config import settings
from app.core.db import async_session_maker
from app.models import Notification, User, DeviceToken

# Tracks retry counts for testing assertions
retry_counts = {}

async def enqueue_task(task_name: str, *args, **kwargs):
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    task_payload = {
        "task_id": str(uuid.uuid4()),
        "task_name": task_name,
        "args": args,
        "kwargs": kwargs
    }
    try:
        await client.rpush("turf_tasks_queue", json.dumps(task_payload))
    finally:
        await client.aclose()


async def send_with_retry(send_func, *args, max_retries: int = 3, **kwargs):
    attempt = 0
    delay = 0.1  # Set short delay for fast test suites execution
    while True:
        try:
            return await send_func(*args, **kwargs)
        except Exception as e:
            attempt += 1
            if attempt > max_retries:
                print(f"Failed to send after {max_retries} attempts: {e}")
                raise e
            sleep_time = delay * (2 ** (attempt - 1)) + random.uniform(0, 0.05)
            print(f"Retry sleep: {sleep_time:.3f}s (Attempt {attempt}/{max_retries})")
            await asyncio.sleep(sleep_time)


# Third-party mocks
async def mock_send_email(email: str, title: str, body: str):
    print(f"[SendGrid Mock] Sending email to {email}: {title} - {body}")
    # Update retry count tracking
    retry_counts[email] = retry_counts.get(email, 0) + 1
    if email == "fail@example.com":
        raise Exception("Network timeout connecting to SendGrid")


async def mock_send_push(token: str, title: str, body: str):
    print(f"[FCM Mock] Sending push notification to token {token}: {title} - {body}")
    # Update retry count tracking
    retry_counts[token] = retry_counts.get(token, 0) + 1
    if token == "fail_token":
        raise Exception("FCM Service Unavailable")


async def handle_send_notification(user_id_str: str, title: str, body: str, notification_type: str):
    user_id = uuid.UUID(user_id_str)
    
    async with async_session_maker() as db:
        user = await db.get(User, user_id)
        if not user:
            print(f"User {user_id} not found, skipping notification")
            return
            
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            type=notification_type,
            read=False
        )
        db.add(notification)
        await db.commit()

        # Try sending email
        try:
            await send_with_retry(mock_send_email, user.email, title, body)
        except Exception as e:
            print(f"Failed to send email to {user.email}: {e}")

        # Try sending push notifications to registered devices
        tokens_statement = select(DeviceToken).where(DeviceToken.user_id == user_id)
        tokens_result = await db.execute(tokens_statement)
        device_tokens = tokens_result.scalars().all()
        
        for dt in device_tokens:
            try:
                await send_with_retry(mock_send_push, dt.token, title, body)
            except Exception as e:
                print(f"Failed to send push notification to token {dt.token}: {e}")


async def process_task(task: dict):
    task_name = task["task_name"]
    args = task["args"]
    kwargs = task["kwargs"]

    if task_name == "send_notification":
        await handle_send_notification(*args, **kwargs)


worker_task: Optional[asyncio.Task] = None

async def worker_loop():
    print("Background worker loop started...")
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        while True:
            # BLPOP blocks until a task is available in the queue
            result = await client.blpop("turf_tasks_queue", timeout=1)
            if result:
                queue_name, task_json = result
                try:
                    task = json.loads(task_json)
                    await process_task(task)
                except Exception as e:
                    print(f"Error processing task in worker loop: {e}")
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        print("Background worker loop cancelled")
    except Exception as e:
        print(f"Background worker loop error: {e}")
    finally:
        await client.aclose()


def start_worker():
    global worker_task
    worker_task = asyncio.create_task(worker_loop())


async def stop_worker():
    global worker_task
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
