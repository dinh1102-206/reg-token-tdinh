import os
import sys
import time
import json
import random
import threading
import websocket
from colorama import Fore

try:
    from pystyle import Colors, Colorate, Center
    HAS_PYSTYLE = True
except ImportError:
    HAS_PYSTYLE = False

if os.name == "nt":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

# Colors
lr = Fore.LIGHTMAGENTA_EX
w = Fore.WHITE
g = Fore.GREEN
RESET = Fore.RESET


class Onliner:
    def __init__(self, token) -> None:
        self.token = token

    def __online__(self):
        try:
            ws = websocket.WebSocket()
            ws.connect("wss://gateway.discord.gg/?encoding=json&v=9")
            response = ws.recv()
            event = json.loads(response)
            heartbeat_interval = int(event["d"]["heartbeat_interval"]) / 1000

            ws.send(
                json.dumps(
                    {
                        "op": 2,
                        "d": {
                            "token": self.token,
                            "properties": {
                                "$os": sys.platform,
                                "$browser": "RTB",
                                "$device": f"{sys.platform} Device",
                            },
                            "presence": {
                                "status": "online",
                                "since": 0,
                                "activities": [],
                                "afk": False,
                            },
                        },
                        "s": None,
                        "t": None,
                    }
                )
            )

            print(f"  {g}[+]{RESET} Online | {self.token[:25]}...")

            while True:
                heartbeatJSON = {"op": 1, "token": self.token, "d": "null"}
                ws.send(json.dumps(heartbeatJSON))
                time.sleep(heartbeat_interval)
        except Exception as e:
            print(f"  {Fore.RED}[-]{RESET} Failed | {self.token[:25]}...")


def main():
    os.system("cls" if os.name == "nt" else "clear")
    os.system("title 9DEVS Token Onliner")

    P = Fore.LIGHTMAGENTA_EX
    R = Fore.RESET
    C = Fore.CYAN

    print(f"\n  {P}┌──────────────────────────────────────────┐{R}")
    print(f"  {P}│{R}  {C}Token Onliner Gateway{R}                    {P}│{R}")
    print(f"  {P}└──────────────────────────────────────────┘{R}\n")

    # Auto-detect token file
    token_paths = [
        os.path.join(os.path.dirname(__file__), "output", "email_verified.txt"),
        os.path.join(os.path.dirname(__file__), "..", "TokenJoiner", "TokenJoiner", "tokens.txt"),
        os.path.join(os.path.dirname(__file__), "..", "Ultimate-Discord-Server-Joiner", "input", "tokens.txt"),
        "tokens.txt",
    ]

    tokens = []
    active_path = None
    for path in token_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                content = [t.strip() for t in f.readlines() if t.strip()]
                if content:
                    tokens = content
                    active_path = path
                    break

    if not tokens:
        print(f"  {Fore.RED}[!]{RESET} No tokens found!")
        input(f"\n  {lr}Press Enter to return...")
        return

    print(f"\n  {g}[*]{RESET} Loaded {len(tokens)} tokens from {active_path}\n")

    for token in tokens:
        # Strip email:pass: prefix
        if ":" in token:
            parts = token.split(":")
            token = parts[-1].strip().strip('"')

        threading.Thread(
            target=Onliner(token).__online__, daemon=True
        ).start()
        time.sleep(0.1)

    print(f"\n  {g}[#]{RESET} All gateway connections established.")
    input(f"  {lr}[>]{RESET} Press ENTER to disconnect and exit...")


if __name__ == "__main__":
    main()
