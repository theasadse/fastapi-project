from collections import OrderedDict, deque
from dataclasses import dataclass
import json
from threading import Lock

from redis import Redis
from redis.exceptions import RedisError


@dataclass
class CachedChatMessage:
    session_id: str
    role: str
    message: str


class ChatCacheService:
    def __init__(
        self,
        per_session_limit: int = 20,
        max_sessions: int = 2000,
    ) -> None:
        self.per_session_limit = per_session_limit
        self.max_sessions = max_sessions
        self.session_ttl_seconds = 86400
        self._session_messages: OrderedDict[str, deque[CachedChatMessage]] = OrderedDict()
        self._pending_writes: deque[CachedChatMessage] = deque()
        self._redis: Redis | None = None
        self._key_prefix = "chat-cache"
        self._lock = Lock()

    def configure_redis(self, redis_url: str, key_prefix: str = "chat-cache") -> bool:
        if not redis_url:
            self._redis = None
            self._key_prefix = key_prefix
            return False

        try:
            client = Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            self._redis = client
            self._key_prefix = key_prefix
            return True
        except RedisError:
            self._redis = None
            self._key_prefix = key_prefix
            return False

    def is_redis_enabled(self) -> bool:
        return self._redis is not None

    def _recent_key(self, session_id: str) -> str:
        return f"{self._key_prefix}:session:{session_id}:recent"

    def _pending_key(self) -> str:
        return f"{self._key_prefix}:pending"

    def _serialize(self, item: CachedChatMessage) -> str:
        return json.dumps(
            {
                "session_id": item.session_id,
                "role": item.role,
                "message": item.message,
            },
            ensure_ascii=False,
        )

    def _deserialize(self, raw: str) -> CachedChatMessage:
        data = json.loads(raw)
        return CachedChatMessage(
            session_id=str(data.get("session_id", "")),
            role=str(data.get("role", "")),
            message=str(data.get("message", "")),
        )

    def get_recent_messages(self, session_id: str, limit: int) -> list[CachedChatMessage]:
        if self._redis is not None:
            raw_items = self._redis.lrange(self._recent_key(session_id), -limit, -1)
            return [self._deserialize(raw) for raw in raw_items]

        with self._lock:
            messages = self._session_messages.get(session_id)
            if messages is None:
                return []
            self._session_messages.move_to_end(session_id)
            return list(messages)[-limit:]

    def warm_session(self, session_id: str, messages: list[CachedChatMessage]) -> None:
        if self._redis is not None:
            key = self._recent_key(session_id)
            trimmed = messages[-self.per_session_limit :]
            payload = [self._serialize(item) for item in trimmed]
            pipe = self._redis.pipeline()
            pipe.delete(key)
            if payload:
                pipe.rpush(key, *payload)
                pipe.expire(key, self.session_ttl_seconds)
            pipe.execute()
            return

        with self._lock:
            session_queue = self._ensure_session(session_id)
            session_queue.clear()
            for item in messages[-self.per_session_limit :]:
                session_queue.append(item)

    def add_message(self, session_id: str, role: str, message: str) -> None:
        if self._redis is not None:
            item = CachedChatMessage(session_id=session_id, role=role, message=message)
            recent_key = self._recent_key(session_id)
            pending_key = self._pending_key()
            raw = self._serialize(item)
            pipe = self._redis.pipeline()
            pipe.rpush(recent_key, raw)
            pipe.ltrim(recent_key, -self.per_session_limit, -1)
            pipe.expire(recent_key, self.session_ttl_seconds)
            pipe.rpush(pending_key, raw)
            pipe.execute()
            return

        with self._lock:
            chat_message = CachedChatMessage(session_id=session_id, role=role, message=message)
            session_queue = self._ensure_session(session_id)
            session_queue.append(chat_message)
            self._pending_writes.append(chat_message)

    def pending_count(self) -> int:
        if self._redis is not None:
            return int(self._redis.llen(self._pending_key()))

        with self._lock:
            return len(self._pending_writes)

    def pop_pending_batch(self, max_items: int) -> list[CachedChatMessage]:
        if self._redis is not None:
            popped = self._redis.lpop(self._pending_key(), count=max_items)
            if not popped:
                return []
            if isinstance(popped, list):
                return [self._deserialize(raw) for raw in popped]
            return [self._deserialize(popped)]

        with self._lock:
            batch: list[CachedChatMessage] = []
            for _ in range(min(max_items, len(self._pending_writes))):
                batch.append(self._pending_writes.popleft())
            return batch

    def pop_session_pending(self, session_id: str) -> list[CachedChatMessage]:
        if self._redis is not None:
            pending_key = self._pending_key()
            raw_items = self._redis.lrange(pending_key, 0, -1)
            if not raw_items:
                return []

            session_items: list[str] = []
            kept_items: list[str] = []
            for raw in raw_items:
                item = self._deserialize(raw)
                if item.session_id == session_id:
                    session_items.append(raw)
                else:
                    kept_items.append(raw)

            pipe = self._redis.pipeline()
            pipe.delete(pending_key)
            if kept_items:
                pipe.rpush(pending_key, *kept_items)
            pipe.execute()

            return [self._deserialize(raw) for raw in session_items]

        with self._lock:
            kept: deque[CachedChatMessage] = deque()
            session_items: list[CachedChatMessage] = []
            while self._pending_writes:
                item = self._pending_writes.popleft()
                if item.session_id == session_id:
                    session_items.append(item)
                else:
                    kept.append(item)

            self._pending_writes = kept
            return session_items

    def clear_session(self, session_id: str) -> None:
        if self._redis is not None:
            self._redis.delete(self._recent_key(session_id))
            self.pop_session_pending(session_id=session_id)
            return

        with self._lock:
            self._session_messages.pop(session_id, None)
            kept: deque[CachedChatMessage] = deque()
            while self._pending_writes:
                item = self._pending_writes.popleft()
                if item.session_id != session_id:
                    kept.append(item)
            self._pending_writes = kept

    def _ensure_session(self, session_id: str) -> deque[CachedChatMessage]:
        session_queue = self._session_messages.get(session_id)
        if session_queue is None:
            session_queue = deque(maxlen=self.per_session_limit)
            self._session_messages[session_id] = session_queue
        self._session_messages.move_to_end(session_id)

        while len(self._session_messages) > self.max_sessions:
            self._session_messages.popitem(last=False)

        return session_queue


chat_cache_service = ChatCacheService()
