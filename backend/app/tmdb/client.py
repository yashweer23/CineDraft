"""Read-only TMDB client. Credentials never enter URLs, checkpoints or errors."""
import json
import random
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import httpx2 as httpx

BASE_URL = "https://api.themoviedb.org/3"
MAX_BYTES = 16 * 1024 * 1024

class TMDBError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)

class TMDBClient:
    def __init__(self, token: str, *, transport=None, sleep=time.sleep,
                 clock=time.monotonic, jitter=lambda: random.uniform(0, .25)):
        if not token or token.strip() != token or any(c.isspace() for c in token):
            raise TMDBError("missing_token", "Set TMDB_READ_ACCESS_TOKEN to your API Read Access Token in backend/.env.")
        self._client = httpx.Client(base_url=BASE_URL, headers={"Authorization": "Bearer " + token,
            "Accept": "application/json", "User-Agent": "CineDraft/0.4 (local catalog import)"},
            timeout=httpx.Timeout(20, connect=5), follow_redirects=False, trust_env=False,
            transport=transport, limits=httpx.Limits(max_connections=1))
        self._sleep, self._clock, self._jitter = sleep, clock, jitter
        self._last = None

    def close(self):
        self._client.close()

    def _retry_after(self, value):
        if not value:
            return None
        try:
            seconds = float(value)
        except ValueError:
            try:
                seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                return None
        if not 0 <= seconds <= 60:
            raise TMDBError("rate_limited", "TMDB requested a longer pause. Resume the import later.")
        return seconds

    def get(self, path, params=None):
        if not re.fullmatch(r"/(configuration|discover/movie|movie/[1-9][0-9]*)", path):
            raise ValueError("Unsupported TMDB read path")
        for attempt in range(4):
            if self._last is not None:
                self._sleep(max(0, .25 - (self._clock() - self._last)))
            self._last = self._clock()
            retry_after = None
            try:
                with self._client.stream("GET", path, params=params) as response:
                    status = response.status_code
                    if status in (401, 403):
                        raise TMDBError("authentication_failed", "TMDB rejected the access token. Check backend/.env.")
                    if status == 404:
                        raise TMDBError("not_found", "TMDB could not find the requested movie.")
                    if status == 429 or 500 <= status <= 599:
                        retry_after = self._retry_after(response.headers.get("Retry-After"))
                        retry = True
                    elif status != 200:
                        raise TMDBError("http_error", "TMDB returned an unexpected status; no response body was logged.")
                    else:
                        retry = False
                        chunks, size = [], 0
                        for chunk in response.iter_bytes():
                            size += len(chunk)
                            if size > MAX_BYTES:
                                raise TMDBError("response_too_large", "TMDB response exceeded the import size limit.")
                            chunks.append(chunk)
                        try:
                            data = json.loads(b"".join(chunks), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                        except (ValueError, UnicodeError):
                            raise TMDBError("invalid_json", "TMDB returned invalid JSON.") from None
                        if not isinstance(data, dict):
                            raise TMDBError("invalid_json", "TMDB returned an unexpected JSON shape.")
                        return data
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError):
                retry = True
            if retry and attempt == 3:
                raise TMDBError("retry_exhausted", "TMDB remained unavailable after four attempts. Resume this import later.") from None
            self._sleep(retry_after if retry_after is not None else min(8, 2**attempt + self._jitter()))
        raise AssertionError("unreachable")

    def configuration(self):
        return self.get("/configuration")

    def discover(self, page: int, cutoff: str):
        if type(page) is not int or not 1 <= page <= 500:
            raise ValueError("Discovery page must be between 1 and 500")
        return self.get("/discover/movie", {"page": page, "language": "en-US", "with_original_language": "en",
            "primary_release_date.lte": cutoff, "include_adult": "false", "include_video": "false",
            "sort_by": "popularity.desc"})

    def movie(self, movie_id: int):
        if type(movie_id) is not int or movie_id <= 0:
            raise ValueError("Movie ID must be a positive integer")
        return self.get(f"/movie/{movie_id}", {"language": "en-US", "append_to_response": "credits,keywords"})
