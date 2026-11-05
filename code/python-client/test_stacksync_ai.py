import json
import threading
import unittest
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, HTTPServer

import stacksync_ai as ai


def serve(script):
    """script: list of (status, body dict). Records requests."""
    seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers["Content-Length"])
            seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": json.loads(self.rfile.read(length))})
            status, body = script[min(len(seen) - 1, len(script) - 1)]
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, seen, f"http://127.0.0.1:{server.server_address[1]}"


OK = (200, {"choices": [{"message": {"content": "hello"}}], "usage": {"cost": "0.00123400", "total_tokens": 42}})
MSG = [{"role": "user", "content": "hi"}]


class ClientTests(unittest.TestCase):
    def call(self, script, **kw):
        server, seen, url = serve(script)
        self.addCleanup(server.shutdown)
        sleeps = []
        kw.setdefault("sleep", sleeps.append)
        try:
            return ai.chat(MSG, model="m1", key="test-key", base_url=url, **kw), seen, sleeps
        except ai.AIError as err:
            err.seen, err.sleeps = seen, sleeps
            raise

    def test_success_returns_text_and_decimal_cost(self):
        result, seen, _ = self.call([OK], max_tokens=100)
        self.assertEqual(result["text"], "hello")
        self.assertEqual(result["cost"], Decimal("0.00123400"))
        self.assertEqual(seen[0]["path"], "/chat/completions")
        self.assertEqual(seen[0]["auth"], "Bearer test-key")
        self.assertEqual(seen[0]["body"]["max_tokens"], 100)

    def test_429_is_retried_with_backoff_then_succeeds(self):
        result, seen, sleeps = self.call([(429, {}), (429, {}), OK])
        self.assertEqual(result["text"], "hello")
        self.assertEqual(len(seen), 3)
        self.assertEqual(sleeps, [1, 2])

    def test_429_gives_up_after_retries(self):
        with self.assertRaises(ai.Busy) as ctx:
            self.call([(429, {})], retries=1)
        self.assertEqual(len(ctx.exception.seen), 2)

    def test_402_is_not_retried(self):
        with self.assertRaises(ai.BudgetExceeded) as ctx:
            self.call([(402, {})])
        self.assertEqual(len(ctx.exception.seen), 1)

    def test_401_is_not_retried(self):
        with self.assertRaises(ai.InvalidKey) as ctx:
            self.call([(401, {})])
        self.assertEqual(len(ctx.exception.seen), 1)

    def test_503_is_ambiguous_and_not_retried(self):
        with self.assertRaises(ai.Unavailable) as ctx:
            self.call([(503, {})])
        self.assertTrue(ctx.exception.ambiguous)
        self.assertEqual(len(ctx.exception.seen), 1)

    def test_max_tokens_is_capped_before_any_request(self):
        with self.assertRaises(ai.AIError):
            ai.chat(MSG, model="m", key="k", max_tokens=ai.MAX_TOKENS_CAP + 1)

    def test_missing_key_or_model(self):
        with self.assertRaises(ai.AIError):
            ai.chat(MSG, model="m", key="")
        with self.assertRaises(ai.AIError):
            ai.chat(MSG, model="", key="k")

    def test_the_key_never_appears_in_an_error_message(self):
        with self.assertRaises(ai.AIError) as ctx:
            self.call([(402, {})])
        self.assertNotIn("test-key", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
