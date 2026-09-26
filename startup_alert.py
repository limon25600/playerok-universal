"""Notify the bot owner about startup failures without changing saved settings."""

import logging
import time

from proxy_utils import requests_proxy


logger = logging.getLogger("universal")


def deliver_startup_alert(config: dict, problem: str, send=None, pause=None) -> bool:
    """Retry until Telegram confirms delivery; return False if no recipient exists."""
    token = config["telegram"]["api"]["token"]
    recipients = config["telegram"]["bot"]["signed_users"]
    if not recipients:
        chat_id = config["playerok"]["notifications"]["chat_id"]
        recipients = [chat_id] if chat_id else []
    if not token or not recipients:
        return False

    if send is None:
        from requests import post
        send = post
    if pause is None:
        pause = time.sleep

    api_url = config["telegram"]["api"]["custom_api_url"] or "https://api.telegram.org"
    if "://" not in api_url:
        api_url = "https://" + api_url
    url = f"{api_url.rstrip('/')}/bot{token}/sendMessage"
    telegram_proxy = config["telegram"]["api"]["proxy"]
    proxies = None
    if telegram_proxy:
        proxy_url = requests_proxy(telegram_proxy)
        proxies = {"http": proxy_url, "https": proxy_url}

    message = (
        f"⚠️ Playerok Universal остановлен. {problem}\n\n"
        "Cookie-данные, User-Agent и прокси сохранены. Проверьте прокси и обновите "
        "Cookie-данные через pluniversal setup. При необходимости переустановите бота "
        "с новыми настройками и восстановите резервную копию."
    )
    while True:
        for chat_id in recipients:
            # A failed Telegram proxy must not also block the emergency alert.
            for active_proxies in ([proxies, None] if proxies else [None]):
                try:
                    response = send(
                        url,
                        json={"chat_id": chat_id, "text": message},
                        proxies=active_proxies,
                        timeout=10,
                    )
                    if response.ok and response.json().get("ok") is True:
                        return True
                except Exception:
                    pass
        logger.warning("Telegram недоступен; повторю отправку уведомления через 60 секунд.")
        pause(60)
