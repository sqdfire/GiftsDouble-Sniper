import requests
import time
import random
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

# Глобальный флаг для остановки снайпера
is_running = False

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

BG_COLOR = "#101010"  # Почти черный фон
F_COLOR = "#FFFFFF"  # Белый текст
ACCENT_PURPLE = "#BB86FC"  # Светло-фиолетовый акцент
DARK_PURPLE = "#1E1E1E"  # Темно-серый/фиолетовый для полей ввода
BTN_START = "#6200EE"  # Ярко-фиолетовый для старта
BTN_STOP = "#CF6679"  # Приглушенный красный для стопа
TEXT_DIM = "#555555"  # Темно-серый текст для подписей в подвале

def log_message(text_widget, message):
    text_widget.config(state=tk.NORMAL)
    text_widget.insert(tk.END, message + "\n")
    text_widget.see(tk.END)  # Автоскролл вниз
    text_widget.config(state=tk.DISABLED)


def sniper_thread(token, max_price, text_widget):
    """Основной цикл снайпера, который работает в отдельном потоке"""
    global is_running

    INVENTORY_URL = "https://api.giftsdouble.xyz/api/withdraw/inventory"
    WITHDRAW_URL = "https://api.giftsdouble.xyz/api/withdraw"

    HEADERS = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": token.encode('utf-8'),
        "User-Agent": random.choice(USER_AGENTS),
        "Origin": "https://www.giftsdouble.xyz",
        "Referer": "https://www.giftsdouble.xyz/"
    }

    session = requests.Session()
    session.headers.update(HEADERS)

    base_delay = 1.0
    penalty_delay = 15
    was_blocked = False

    log_message(text_widget, "[*] Снайпер запущен! Жду появление подарков...")

    while is_running:
        try:
            resp = session.get(INVENTORY_URL)

            if resp.status_code == 429:
                log_message(text_widget, f"[-] Блокировка от спама (429). Ждем {penalty_delay} сек...")
                time.sleep(penalty_delay)
                log_message(text_widget, "[*] Пробую снова...")
                penalty_delay += 10
                was_blocked = True
                continue
            else:
                # Если до этого были в бане, а теперь код ответа нормальный
                if was_blocked and resp.status_code == 200:
                    log_message(text_widget, "[+] Блокировка прошла! Продолжаю снайпить...")
                    was_blocked = False

                penalty_delay = 15  # Сбрасываем штрафное время

            if resp.status_code == 403:
                log_message(text_widget, "[-] Ошибка 403 Forbidden! Токен неверный или протух.")
                is_running = False
                break

            if resp.status_code != 200:
                log_message(text_widget, f"[!] Ошибка сервера: {resp.status_code}")
                time.sleep(2)
                continue

            data = resp.json()
            items = data.get("items", [])
            found_cheap = False

            for item in items:
                if not is_running:
                    break  # Прерываем, если нажали СТОП

                price = item.get("price", 999999)
                slug = item.get("slug", "")

                if price <= max_price:
                    log_message(text_widget, f"[!] НАШЕЛ! {item['title']} за {price}. Вывожу...")
                    payload = {"slugs": [slug]}

                    withdraw_resp = session.post(WITHDRAW_URL, json=payload)

                    if withdraw_resp.status_code == 403:
                        log_message(text_widget, "[-] Не успели: Forbidden (Отклонено сервером)")
                    elif withdraw_resp.status_code == 429:
                        log_message(text_widget, "[-] Не успели: 429 Too Many Requests")
                    else:
                        withdraw_data = withdraw_resp.json()
                        if withdraw_data.get("success"):
                            log_message(text_widget, f"[+] УСПЕХ! Подарок {slug} выведен!")
                            is_running = False  # Останавливаемся после успеха
                            return
                        else:
                            log_message(text_widget,
                                        f"[-] Не успели: {withdraw_data.get('error', 'Неизвестная ошибка')}")

                    found_cheap = True
                    break

            if not found_cheap and is_running:
                time.sleep(base_delay)

        except Exception as e:
            if is_running:
                log_message(text_widget, f"[X] Ошибка соединения: {e}")
                time.sleep(2)

    log_message(text_widget, "[*] Снайпер остановлен.")


def start_sniper(token_entry, price_entry, text_widget, start_btn, stop_btn):
    global is_running

    token = token_entry.get().strip()
    try:
        max_price = int(price_entry.get().strip())
    except ValueError:
        messagebox.showerror("Ошибка", "Максимальная цена должна быть числом!")
        return

    if not token:
        messagebox.showerror("Ошибка", "Введите токен авторизации!")
        return

    is_running = True
    start_btn.config(state=tk.DISABLED, bg="#333333")  # Делаем кнопку серой при отключении
    stop_btn.config(state=tk.NORMAL, bg=BTN_STOP)

    # Запускаем в отдельном потоке
    threading.Thread(target=sniper_thread, args=(token, max_price, text_widget), daemon=True).start()


def stop_sniper(start_btn, stop_btn):
    global is_running
    is_running = False
    start_btn.config(state=tk.NORMAL, bg=BTN_START)
    stop_btn.config(state=tk.DISABLED, bg="#333333")


# --- Создание интерфейса ---
root = tk.Tk()
root.title("GiftsDouble Sniper")
root.geometry("600x530")
root.configure(padx=15, pady=10, bg=BG_COLOR)

# Поле для токена
tk.Label(root, text="Токен авторизации (F12->Network):", font=("Consolas", 10, "bold"), fg=F_COLOR, bg=BG_COLOR).pack(
    anchor="w", pady=(10, 0))
token_entry = tk.Entry(root, width=90, bg=DARK_PURPLE, fg=F_COLOR, insertbackground=F_COLOR, relief=tk.FLAT)
token_entry.pack(pady=5, ipady=3)  # Добавили внутренний отступ для красоты

# Поле для цены
tk.Label(root, text="Максимальная цена (монеты):", font=("Consolas", 10, "bold"), fg=F_COLOR, bg=BG_COLOR).pack(
    anchor="w", pady=(10, 0))
price_entry = tk.Entry(root, width=90, bg=DARK_PURPLE, fg=F_COLOR, insertbackground=F_COLOR, relief=tk.FLAT)
price_entry.insert(0, "4000")  # Значение по умолчанию
price_entry.pack(pady=5, ipady=3)

# Кнопки
btn_frame = tk.Frame(root, bg=BG_COLOR)
btn_frame.pack(pady=15)

start_btn = tk.Button(btn_frame, text="СТАРТ", font=("Arial", 10, "bold"), bg=BTN_START, fg=F_COLOR, width=18,
                      relief=tk.FLAT, activebackground=ACCENT_PURPLE)
stop_btn = tk.Button(btn_frame, text="СТОП", font=("Arial", 10, "bold"), bg="#333333", fg=F_COLOR, width=18,
                     relief=tk.FLAT, state=tk.DISABLED, activebackground="#FF8080")

start_btn.config(command=lambda: start_sniper(token_entry, price_entry, log_text, start_btn, stop_btn))
stop_btn.config(command=lambda: stop_sniper(start_btn, stop_btn))

start_btn.pack(side=tk.LEFT, padx=10)
stop_btn.pack(side=tk.LEFT, padx=10)

# Окно логов
tk.Label(root, text="Логи работы:", font=("Arial", 10, "bold"), fg=F_COLOR, bg=BG_COLOR).pack(anchor="w")
log_text = scrolledtext.ScrolledText(root, width=70, height=15, state=tk.DISABLED, bg="#050505", fg=ACCENT_PURPLE,
                                     font=("Consolas", 9), relief=tk.FLAT, borderwidth=0)
log_text.pack(pady=5)

# --- Подвал (Версия и Копирайт) ---
bottom_frame = tk.Frame(root, bg=BG_COLOR)
bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))

version_label = tk.Label(bottom_frame, text="v0.1", font=("Arial", 9, "bold"), fg=TEXT_DIM, bg=BG_COLOR)
version_label.pack(side=tk.LEFT)

created_by_label = tk.Label(bottom_frame, text="Created by @soonfomo", font=("Arial", 9, "bold"), fg=TEXT_DIM,
                            bg=BG_COLOR)
created_by_label.pack(side=tk.RIGHT)

root.mainloop()