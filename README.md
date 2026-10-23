# LUDOMAN Case — starter project

Telegram Mini App demo with virtual cases, server-side rewards, balance and inventory.
This is a starter/demo project: it does **not** send real Telegram gifts, mint NFTs, accept payments, or provide withdrawals.

## Requirements
- Python 3.11+
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- For Telegram use: a public HTTPS URL for this app

## 1. Run locally

### Windows
1. Install Python from https://www.python.org/downloads/ (enable "Add Python to PATH").
2. Extract the ZIP and open the `ludoman_case` folder.
3. Copy `.env.example` to `.env`.
4. Leave `DEV_MODE=1` for local browser testing. You can leave `BOT_TOKEN` empty if testing only the web demo.
5. Open PowerShell in the project folder and run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Open http://127.0.0.1:8000 in your browser.

### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Open http://127.0.0.1:8000.

## 2. Connect Telegram

1. In Telegram, open @BotFather and use `/newbot`.
2. Copy the token into `.env` as `BOT_TOKEN=...`.
3. Deploy the project to a host that supports Python and HTTPS. Set environment variables:
   - `BOT_TOKEN`: your actual token
   - `WEBAPP_URL`: the public HTTPS URL of your app, e.g. `https://your-project.example.com`
   - `DEV_MODE=0`
   - `PORT`: the port specified by the host (if required)
4. Ensure the host provides persistent storage for `ludoman.sqlite3` if you want data to survive restarts. Set `DATA_DIR` to that persistent disk path.
5. Restart the service, then send `/start` to your bot. The Mini App button will open your app.

Important: `WEBAPP_URL` must be a real public HTTPS URL. A localhost address will not work from Telegram.

## 3. What is included
- Three demo cases (Starter, Premium, Daily)
- Virtual balance and server-side weighted rewards
- Daily case cooldown (24 hours)
- Inventory and recent opening records stored in SQLite
- Telegram Web App `initData` signature validation when `DEV_MODE=0`
- Mobile-friendly dark green interface

## 4. Before going live
- Set `DEV_MODE=0`.
- Never commit `.env` or expose the bot token.
- Use persistent database storage or migrate to PostgreSQL.
- Add rate limiting, monitoring, backups, support/contact details, terms and privacy policy.
- Keep case odds visible and use a secure server-side random outcome.
- For digital goods sold inside Telegram, follow Telegram Stars requirements and current Telegram policies.
- Real Telegram gifts and NFT transfers need separate integration and careful testing. The demo's "NFT" label is only a virtual demo item.
- Do not treat demo coins or item values as money. No deposit, cashout or real-money gambling feature is implemented.

## 5. Customize
Edit `CASES` and `REWARDS` near the top of `main.py`. Reward `weight` values are relative weights within a case; for example weights 65, 25, 9, 1 correspond to 65%, 25%, 9%, 1% because they sum to 100.
Edit `web/style.css` for colors and `web/index.html` for layout.

## Troubleshooting
- `Открой приложение через Telegram`: open through the bot's Web App button, not a normal browser, unless local `DEV_MODE=1`.
- Bot does not respond: verify `BOT_TOKEN`, check that only one bot polling instance is running, and restart.
- Telegram button does not appear: verify `WEBAPP_URL` is a public HTTPS URL and restart the service.
- Data disappears after deploy: configure persistent storage and set `DATA_DIR` to it.
