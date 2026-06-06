"""Telegram bot front-end for the Urban Independence agent.

Wraps Orchestrator the same way demo_cli.py does, but with Telegram chats as the
transport. One session per Telegram chat. Long-polls getUpdates; no webhook needed.

Commands (single-arg, BotFather-friendly):
    /start   begin a new training session (elders only)
    /end     end the current session
    /link    begin a step-by-step linking flow
    /cancel  abort the current /link flow
    /whoami  show how this chat is linked
    /help    show commands

Any other text is forwarded to Orchestrator.turn() and the reply is sent back.

Env:
    ANTHROPIC_API_KEY    (required)
    TELEGRAM_BOT_TOKEN   (required)

Run:
    python telegram_bot.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

import httpx
from dotenv import load_dotenv

from agent import Orchestrator, Store
from agent.config import ElderProfile

TELEGRAM_API = "https://api.telegram.org"

HELP_TEXT = (
    "Urban Independence training bot.\n\n"
    "/link    — link this chat to an elder (step-by-step)\n"
    "/whoami  — show how this chat is linked\n"
    "/start   — begin a new scenario (elders only)\n"
    "/end     — end the current session\n"
    "/cancel  — abort the current /link flow\n"
    "/help    — show this message\n\n"
    "Anything else is treated as your response to the coach."
)


def _profile_for(elder_id: str, first_name: str | None) -> ElderProfile:
    """Profile is keyed on the registered elder_id. Demographics are a placeholder
    until a proper elder-profile table exists."""
    return ElderProfile(
        elder_id=elder_id,
        name=first_name or "Friend",
        age=78,
        home_district="Sham Shui Po",
        mobility="walks slowly with a cane, gets winded on stairs",
        health_notes=["mild hypertension", "doesn't drink enough water on hot days"],
        languages=["Cantonese", "English"],
    )


class TelegramBot:
    def __init__(self, token: str, orch: Orchestrator, store: Store) -> None:
        self.base = f"{TELEGRAM_API}/bot{token}"
        self.orch = orch
        self.store = store
        self.sessions: dict[int, str] = {}                  # chat_id -> session_id
        self.pending_link: dict[int, dict[str, str]] = {}   # chat_id -> {"step", "role"?}
        self.offset: int | None = None
        self.http = httpx.Client(timeout=35.0)              # > long-poll timeout
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    # ── transport helpers ────────────────────────────────────────────────

    def _call(self, method: str, **payload: Any) -> dict[str, Any]:
        r = self.http.post(f"{self.base}/{method}", json=payload)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            raise RuntimeError(f"telegram {method} failed: {data}")
        return data

    def send(self, chat_id: int, text: str) -> None:
        for i in range(0, len(text), 4000):
            self._call("sendMessage", chat_id=chat_id, text=text[i : i + 4000])

    # ── /link state machine ─────────────────────────────────────────────

    def begin_link(self, chat_id: int) -> None:
        self.pending_link[chat_id] = {"step": "role"}
        self.send(
            chat_id,
            "Linking this chat. What's your role? Reply with one word: elder or caregiver.",
        )

    def continue_link(
        self, chat_id: int, text: str, username: str | None, first_name: str | None
    ) -> None:
        state = self.pending_link[chat_id]
        if state["step"] == "role":
            role = text.strip().lower()
            if role not in {"elder", "caregiver"}:
                self.send(chat_id, "Please reply with exactly 'elder' or 'caregiver'.")
                return
            state["role"] = role
            state["step"] = "elder_id"
            self.send(
                chat_id,
                f"Got it — {role}. Now reply with the elder_id this chat belongs to "
                "(e.g. demo-elder-1).",
            )
            return
        if state["step"] == "elder_id":
            elder_id = text.strip()
            if not elder_id or " " in elder_id:
                self.send(chat_id, "Elder id can't be empty or contain spaces. Try again.")
                return
            role = state["role"]
            try:
                self.store.link_telegram(
                    chat_id=chat_id, role=role, elder_id=elder_id,
                    username=username, first_name=first_name,
                )
            except Exception as e:  # noqa: BLE001
                self.send(chat_id, f"Couldn't link: {e}")
                self.pending_link.pop(chat_id, None)
                return
            self.pending_link.pop(chat_id, None)
            self.send(chat_id, f"Linked. Role: {role}, elder_id: {elder_id}.")

    def cancel_link(self, chat_id: int) -> None:
        if self.pending_link.pop(chat_id, None):
            self.send(chat_id, "Link flow cancelled.")
        else:
            self.send(chat_id, "Nothing to cancel.")

    # ── other handlers ──────────────────────────────────────────────────

    def handle_whoami(self, chat_id: int) -> None:
        acct = self.store.get_telegram_account(chat_id)
        if not acct:
            self.send(chat_id, "This chat isn't linked. Send /link to register.")
            return
        self.send(
            chat_id,
            f"Role: {acct['role']}\nElder ID: {acct['elder_id']}\nLinked at: {acct['linked_at']}",
        )

    def handle_start(self, chat_id: int, first_name: str | None) -> None:
        acct = self.store.get_telegram_account(chat_id)
        if not acct or acct["role"] != "elder":
            self.send(
                chat_id,
                "This chat isn't registered as an elder. Send /link first.",
            )
            return
        if chat_id in self.sessions:
            self.send(chat_id, "You already have a session running. Send /end first.")
            return
        self.send(chat_id, "Starting a new session — fetching live HK data… (this can take ~10s)")
        elder = _profile_for(acct["elder_id"], acct.get("first_name") or first_name)
        try:
            session = self.orch.start_session(elder)
        except Exception as e:  # noqa: BLE001
            self.send(chat_id, f"Couldn't start a session: {e}")
            return
        self.sessions[chat_id] = session.id

        s = session.scenario
        lines = [
            s.title,
            "",
            s.setting,
            "",
            f"Goal: {s.goal}",
            "",
            "Live factors:",
            *[f"  • {f}" for f in s.live_factors],
            "",
            "Options:",
            *[f"  ({o.label}) {o.text}" for o in s.options],
            "",
            "What would you do, and why?",
        ]
        self.send(chat_id, "\n".join(lines))

    def handle_end(self, chat_id: int) -> None:
        sid = self.sessions.pop(chat_id, None)
        if not sid:
            self.send(chat_id, "No active session.")
            return
        self.orch.end_session(sid, summary="ended via telegram")
        self.send(chat_id, "Session ended. Send /start to begin another.")

    def handle_text(self, chat_id: int, text: str) -> None:
        sid = self.sessions.get(chat_id)
        if not sid:
            self.send(chat_id, "No active session. Send /start to begin.")
            return
        try:
            reply = self.orch.turn(sid, text)
        except Exception as e:  # noqa: BLE001
            self.send(chat_id, f"(error generating reply: {e})")
            return
        self.send(chat_id, reply)

    # ── update dispatcher ───────────────────────────────────────────────

    def process(self, update: dict[str, Any]) -> None:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            print(f"  [skip] non-message update: {list(update.keys())}")
            return
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()
        sender = msg.get("from") or {}
        first_name = sender.get("first_name")
        username = sender.get("username")
        print(f"  [{chat_id}] {sender.get('first_name', '?')}: {text!r}")
        if not text:
            return

        # Slash command? Strip any "@botname" suffix Telegram adds in groups.
        is_command = text.startswith("/")
        cmd = text.split()[0].split("@")[0] if is_command else ""

        if cmd == "/cancel":
            self.cancel_link(chat_id)
            return

        # Mid-link flow eats any non-command text.
        if chat_id in self.pending_link and not is_command:
            self.continue_link(chat_id, text, username, first_name)
            return
        # If a command arrives mid-flow, treat as an implicit cancel + run the command.
        if chat_id in self.pending_link and is_command:
            self.pending_link.pop(chat_id, None)
            self.send(chat_id, "(link flow cancelled)")

        if cmd == "/start":
            self.handle_start(chat_id, first_name)
        elif cmd == "/end":
            self.handle_end(chat_id)
        elif cmd == "/help":
            self.send(chat_id, HELP_TEXT)
        elif cmd == "/link":
            self.begin_link(chat_id)
        elif cmd == "/whoami":
            self.handle_whoami(chat_id)
        elif is_command:
            self.send(chat_id, f"Unknown command: {cmd}. Send /help.")
        else:
            self.handle_text(chat_id, text)

    # ── runtime ─────────────────────────────────────────────────────────

    def preflight(self) -> None:
        """Verify the token and clear any conflicting webhook before polling."""
        try:
            me = self._call("getMe")["result"]
            print(f"  connected as @{me.get('username')} (id={me.get('id')})")
        except Exception as e:
            print(f"  getMe failed — token likely bad: {e}")
            raise
        try:
            self._call("deleteWebhook", drop_pending_updates=False)
            print("  webhook cleared (long-polling enabled)")
        except Exception as e:  # noqa: BLE001
            print(f"  deleteWebhook warning: {e}")

    def run(self) -> None:
        print("[telegram] starting…")
        self.preflight()
        print("[telegram] polling for updates")
        while not self._stop:
            try:
                params: dict[str, Any] = {"timeout": 25}
                if self.offset is not None:
                    params["offset"] = self.offset
                r = self.http.get(f"{self.base}/getUpdates", params=params)
                r.raise_for_status()
                data = r.json()
                if not data.get("ok"):
                    print(f"[telegram] getUpdates not-ok: {data}")
                    time.sleep(3)
                    continue
                for upd in data.get("result", []):
                    self.offset = upd["update_id"] + 1
                    try:
                        self.process(upd)
                    except Exception as e:  # noqa: BLE001
                        print(f"[telegram] handler error: {e}")
            except KeyboardInterrupt:
                print("\n[telegram] stopping.")
                return
            except Exception as e:  # noqa: BLE001
                if self._stop:
                    return
                print(f"[telegram] poll error: {e}; retrying in 3s")
                time.sleep(3)
        print("[telegram] stopped.")


def main() -> None:
    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set.")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN not set.")

    store = Store()
    orch = Orchestrator(store=store)
    TelegramBot(token=token, orch=orch, store=store).run()


if __name__ == "__main__":
    main()
