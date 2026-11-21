# Gotchas (learned building Jaz, Nov 2026)

Read this before writing level 4-5 code. Each one cost real time once.

## MCP Python SDK v2 (`mcp>=2`)

- `FastMCP` is gone: `from mcp.server.mcpserver import MCPServer, Context`.
- Tools read HTTP headers with `ctx.headers` (None on stdio).
- HTTP app: `mcp.streamable_http_app(streamable_http_path="/mcp", host=..., transport_security=TransportSecuritySettings(allowed_hosts=[...]))`.
  Forgetting `allowed_hosts` for your public hostname gets every request rejected (DNS-rebinding guard).
- Extra routes: `@mcp.custom_route("/healthz", methods=["GET"])`.
- Client: `from mcp import Client`. `Client("http://host/mcp")`, `Client(StdioServerParameters(...))`, or
  `Client(streamable_http_client(url, http_client=httpx2.AsyncClient(headers=...)))` for custom headers.
- The SDK uses **httpx2**, not httpx.

## stdio servers

- Anything a library prints to stdout corrupts the protocol. Dup the real stdout for MCP and point fd 1
  at stderr (see the level 4 template `run_stdio`).
- Claude Code finds the command on PATH. Install with `uv tool install` so it lands in `~/.local/bin`.

## Claude Code plugins

- Layout like i-have-adhd: `.claude-plugin/marketplace.json` with `"source": "./"`, `.claude-plugin/plugin.json`,
  `skills/<name>/SKILL.md`, `.mcp.json` at the repo root.
- Secrets: `userConfig` with `"sensitive": true`, used in `.mcp.json` as `${user_config.api_key}`.
- Plugin MCP servers are named `plugin:<plugin>:<server>` (`claude mcp get plugin:jaz:jaz`).
- Always run `claude plugin validate <dir>`.
- claude.ai custom connectors take a URL, not custom headers: accept the key in the URL (`/mcp/<key>`).

## Python libraries

- authlib >= 1.9 integrates with httpx2. With plain httpx, wrap `authlib.oauth1.ClientAuth` in an `httpx.Auth`.
- faster-whisper 1.2 + new PyAV crashes on `metadata_errors`: decode audio with ffmpeg to float32 yourself.
- CTranslate2 runs on the Apple GPU with `device="mps"` (about 2x CPU), int8 becomes float16 there.
- `rapidocr` 3.x keeps spaces between words; `rapidocr_onnxruntime` 1.4 drops them.
- yt-dlp needs a JS runtime for YouTube: `js_runtimes={"node": {"path": ...}}`.

## Shell (zsh on macOS)

- `for f in $VAR` does NOT split on newlines in zsh. Use `... | while IFS= read -r f; do ...; done`.
- `git mv -k` silently does nothing on untracked files.
- Keg-only Homebrew formulas (`node@24`) are not on PATH; use the full `/opt/homebrew/opt/<f>/bin/...` path.

## X API

- Posting is pay-per-use: about $0.015 per post, $0.20 if it contains a link (check docs.x.com pricing).
- OAuth 1.0a keys: "Consumer Key/Secret" = API Key/Secret. Regenerate the Access Token after switching
  the app to Read and write.
