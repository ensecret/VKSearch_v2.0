import os
import time
import vk_api
import telebot
import json
from datetime import datetime
from dotenv import load_dotenv
from threading import Thread

# Загрузка токенов из .env файла
load_dotenv()

VK_ACCESS_TOKEN = os.getenv('VK_ACCESS_TOKEN')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Инициализация VK API
vk_session = vk_api.VkApi(token=VK_ACCESS_TOKEN)
vk = vk_session.get_api()

# Инициализация Telegram Bot API
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# Функция для сохранения chat_id в файл
def save_chat_id(chat_id):
    try:
        with open("chat_ids.json", "r") as file:
            chat_ids = json.load(file)
    except FileNotFoundError:
        chat_ids = []

    if chat_id not in chat_ids:
        chat_ids.append(chat_id)
        with open("chat_ids.json", "w") as file:
            json.dump(chat_ids, file)


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    save_chat_id(chat_id)
    bot.reply_to(message, "Привет! Теперь ты в списке для получения уведомлений.")


# Функция для загрузки обработанных постов
def load_processed_posts():
    try:
        with open("processed_posts.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []


# Функция для сохранения обработанных постов
def save_processed_posts(processed_posts):
    with open("processed_posts.json", "w") as file:
        json.dump(processed_posts, file)


# Функция поиска публикаций и отправки сообщений
def search_and_send_posts(query):
    processed_posts = load_processed_posts()
    offset = 0  # Начальное смещение

    while True:
        new_posts = []
        try:
            search_results = vk.newsfeed.search(q=query, count=50, offset=offset)  # Поиск 50 постов с текущим смещением
            if not search_results.get('items'):
                print("Нет новых постов для отправки.")
                break  # Если нет больше результатов, выходим из цикла
        except Exception as e:
            print(f"Ошибка при поиске постов: {e}")
            time.sleep(60)
            continue

        for post in search_results['items']:
            post_id = post['id']
            if post_id not in processed_posts:
                user_id = post['from_id']
                profile_link = f"https://vk.com/id{user_id}" if user_id > 0 else f"https://vk.com/club{abs(user_id)}"
                post_link = f"https://vk.com/wall{user_id}_{post_id}"
                post_date = datetime.fromtimestamp(post['date']).strftime('%Y-%m-%d %H:%M:%S')
                message = (f"Найдена публикация:\n{post_link}\n"
                           f"Профиль автора: {profile_link}\n"
                           f"Дата: {post_date}")

                try:
                    send_to_all(message)
                    new_posts.append(post_id)
                except Exception as e:
                    print(f"Ошибка при отправке сообщения: {e}")

        processed_posts.extend(new_posts)
        save_processed_posts(processed_posts)

        offset += 50  # Увеличиваем смещение для следующего запроса
        time.sleep(1800)  # Задержка в 30 минут перед следующим поиском


# Функция отправки сообщений всем chat_id
def send_to_all(message):
    try:
        with open("chat_ids.json", "r") as file:
            chat_ids = json.load(file)
    except FileNotFoundError:
        print("Файл chat_ids.json не найден.")
        return

    for chat_id in chat_ids:
        while True:
            try:
                bot.send_message(chat_id, message)
                time.sleep(0.1)  # Небольшая задержка между отправками
                break
            except telebot.apihelper.ApiTelegramException as e:
                if e.result.status_code == 429:
                    # Если ошибка 429, ждем указанное время
                    retry_after = int(e.result.json()['parameters']['retry_after'])
                    print(f"Слишком много запросов. Ждем {retry_after} секунд.")
                    time.sleep(retry_after)
                else:
                    print(f"Ошибка при отправке сообщения в чат {chat_id}: {e}")
                    break


# Основной цикл программы
def main():
    query = "подписывайтесь на мой канал на ютуб"
    search_and_send_posts(query)


# Запуск бота в отдельном потоке
if __name__ == "__main__":
    Thread(target=main).start()
    bot.polling()