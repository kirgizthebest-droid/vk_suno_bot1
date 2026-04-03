from flask import Flask, request
import vk_api
from vk_api.utils import get_random_id
import requests
import os
import time

app = Flask(__name__)

# ===== Вставь свои ключи =====
VK_TOKEN = "vk1.a.yHRjlGZz32DpRfH6EP9s3_pFOC12x8Rr_JvuAIpKW2Y4P8A5G1bJKr5qYLr_4CAxC7-gDTKFcoKaXtWLf9iPek82vvVB8AbxJkSBbvCwIzNfnxQBJk8acUjmzLdp79SFGsfY0g3CHAYVTtA3VRruyU9WrnA-3evntzrjUBeD2l06EQ1YRk2FrhwCtKfJPCGPiBaGu_kkhInzT7NWRF-Zig"
SUNO_API_KEY = "1b9544b2a524d363c7ad40babfcf058e"
CONFIRMATION_TOKEN = "e8f8753e"
# ============================

vk_session = vk_api.VkApi(token=VK_TOKEN)
vk = vk_session.get_api()

questions = [
    "🎵 Какой стиль музыки? (рэп, поп, рок, классика)",
    "📝 О чём песня?",
    "👤 Для кого песня?",
    "😎 Какое настроение песни?",
    "💬 Добавить конкретные слова или имя?"
]

users = {}  # состояние пользователей

def send_message(user_id, text):
    try:
        vk.messages.send(
            user_id=user_id,
            message=text,
            random_id=get_random_id()
        )
        print(f"Сообщение отправлено {user_id}: {text}")
    except Exception as e:
        print("Ошибка при отправке:", e)

# Функция для проверки результата задачи Suno
def get_song_result(task_id):
    url = f"https://api.sunoapi.org/api/v1/result/{task_id}"
    headers = {"Authorization": f"Bearer {SUNO_API_KEY}"}
    
    for i in range(30):  # проверяем до 30 раз
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = r.json()
            if data.get("data") and data["data"].get("audioUrl"):
                return data["data"]["audioUrl"]
        time.sleep(2)  # ждем 2 секунды перед следующей проверкой
    return None

# Функция генерации песни
def generate_song(prompt):
    url = "https://api.sunoapi.org/api/v1/generate"
    headers = {
        "Authorization": f"Bearer {SUNO_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "customMode": True,
        "instrumental": True,
        "model": "V4_5ALL",
        "prompt": prompt,
        "style": "Pop",
        "title": "Generated Song",
        "vocalGender": "m",
        "styleWeight": 0.65,
        "weirdnessConstraint": 0.65,
        "audioWeight": 0.65
    }
    
    try:
        # Отправка задачи на генерацию
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        task_id = response.json()["data"]["taskId"]
        # Получаем результат
        return get_song_result(task_id)
    except Exception as e:
        print("Ошибка Suno:", e)
        return None

@app.route("/", methods=["POST"])
def main():
    data = request.get_json()
    if "type" not in data:
        return "ok"

    # Подтверждение сервера
    if data["type"] == "confirmation":
        return CONFIRMATION_TOKEN

    # Новое сообщение
    if data["type"] == "message_new":
        user_id = data["object"]["message"]["from_id"]
        text = data["object"]["message"]["text"].strip()

        # Инициализация пользователя
        if user_id not in users:
            users[user_id] = {"step": 0, "answers": []}
            send_message(user_id, "Привет! Давай создадим твою песню 🎶")
            send_message(user_id, questions[0])
            return "ok"

        user_state = users[user_id]

        # Сохраняем ответ
        user_state["answers"].append(text)
        user_state["step"] += 1

        # Если есть следующий вопрос
        if user_state["step"] < len(questions):
            send_message(user_id, questions[user_state["step"]])
        else:
            # Все ответы собраны, формируем промт
            prompt = " | ".join(user_state["answers"])
            send_message(user_id, "⏳ Генерирую песню, подожди немного...")

            song_url = generate_song(prompt)
            if song_url:
                send_message(user_id, f"🎧 Готово! Слушай песню: {song_url}")
            else:
                send_message(user_id, "❌ Ошибка при генерации песни. Попробуй ещё раз.")

            # Сбрасываем состояние
            users.pop(user_id)

        return "ok"

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
