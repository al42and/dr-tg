import logging
from grab.error import GrabTimeoutError
from telepot import Bot
import settings
import re
import time
from io import BytesIO
from raven import Client

from parser import Parser
from views import sector_text, KoImg

CORD_RE = r'(\d{2}[\.,]\d{3,})'
STANDARD_CODE_PATTERN = r'\d*[dr]\d*[dr]\d*'

HELP_TEXT = '''
/status - общая информация о подключении к движку. Используйте ее, чтобы понять, авторизованы ли вы и установлен ли пин.
Настройки /parse, /type можно включать так: "/parse on" и выключать так: "/parse off".
/parse - парсинг движка дозора.
/type - ввод кодов.
/set dont_notify_bonus on - не отправлять в канал сообщения о взятых бонусных кодах.
/set maps off - не отправлять карту в ответ на корды.

/pattern - регулярное выражение для поиска кода. Чтобы установить стандартное выражение используйте команду "/pattern standard".
/link - ссылка в движочек. Для настройки используйте команду "/link <ссылка>", для вывода актуальной ссылки - просто "/link".
/ko - прислать актуальную табличку с КО в чат.
/img - прислать актуальную изображение с КО в чат.
/ код - послать в движок код без проверки на паттерн (см. выше, /pattern). Нужно, если вы не хотите заниматься настройкой паттерна, и вам просто нужно пробить произвольный код.
'''

ADMIN_HELP_TEXT = '''
/auth - авторизация через логин пароль. Использовать так: "/auth login parol". Используйте этот метод авторизации, если у вас есть отдельный аккаунта для бота.
/cookie - установка авторизационной куки dozorSiteSession. Использовать так: "/cookie KTerByfGopF5dSgFjkl07x8v". Используйте этот метод авторизации, если у вас нет отдельного аккаунта для бота и вы используйте один аккаунт как для бота, так и в браузере.
'''

HELP_TEXT += ADMIN_HELP_TEXT


class DzrBot(Bot):
    parse = False  # Режим парсинга движка
    type = False  # Режим ввода кодов
    maps = True
    sentry = None
    code_pattern = None
    sleep_seconds = 30

    routes = (
        (CORD_RE, 'on_cord'),
        (r'^/auth', 'on_auth'),
        (r'^/cookie', 'on_cookie'),
        (r'^/help', 'on_help'),
        (r'^/ko', 'on_ko'),
        (r'^/img', 'on_img'),
        (r'^/link', 'on_link'),
        (r'^/get_chat_id', 'on_get_chat_id'),
        (r'^/parse', 'on_parse'),
        (r'^/pattern', 'on_pattern'),
        (r'^/sleep_seconds', 'on_sleep_seconds'),
        (r'^/status', 'on_status'),
        (r'^/test_error', 'on_test_error'),
        (r'^/type', 'on_type'),
        (r'^/set', 'on_set'),
    )

    bool_options = (
        'dont_notify_bonus',
        'type',
        'parse',
        'maps',
    )

    def set_data(self, key, value):
        setattr(self, key, value)
        self.parser.table_bot.upsert({
            'token': settings.TOKEN,
            key: value
        }, ['token'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = Parser()
        if hasattr(settings, 'SENTRY_DSN') and settings.SENTRY_DSN:
            self.sentry = Client(settings.SENTRY_DSN)

        self.parser.table_bot.upsert({'token': settings.TOKEN}, ['token'])
        data = self.parser.table_bot.find_one(**{'token': settings.TOKEN})
        for key in [
            'type',
            'parse',
            'sleep_seconds',
            'code_pattern',
            'maps'
        ]:
            value = data.get(key)
            if value is not None:
                setattr(self, key, value)

        cookie = data.get('cookie')
        if cookie:
            self.parser.set_cookie(cookie)

    def on_help(self, chat_id, text, msg):
        self.sendMessage(chat_id, HELP_TEXT)

    def on_set(self, chat_id, text, msg):
        try:
            text = text[5:]
            key, value = text.split(' ', 2)
            if key in self.bool_options:
                self.set_data(key, value == 'on')
                self.sendMessage(chat_id, "set {} {}".format(key, value))
        except ValueError:
            pass

    def on_type(self, chat_id, text, msg):
        if 'on' in text:
            self.set_data('type', True)
        elif 'off' in text:
            self.set_data('type', False)
        self.sendMessage(chat_id, "Режим ввода кодов: {}".format("Включен" if self.type else "Выключен"))

    def on_get_chat_id(self, chat_id, text, msg):
        self.sendMessage(chat_id, "chat id: {}".format(msg['chat']['id']))

    def on_parse(self, chat_id, text, msg):
        if 'on' in text:
            self.set_data('parse', True)
        elif 'off' in text:
            self.set_data('parse', False)
        self.sendMessage(chat_id, "Режим парсинга движка: {}".format("Включен" if self.parse else "Выключен"))

    def on_cookie(self, chat_id, text, msg):
        for cookie in re.findall(r'(\w{32})', text):
            cookie = cookie.upper()
            self.parser.set_cookie(cookie)
            self.set_data('cookie', cookie)
            self.sendMessage(chat_id, "Кука установлена")

    def on_test_error(self, chat_id, text, msg):
        raise Exception

    def on_auth(self, chat_id, text, msg):
        try:
            login, password = map(
                lambda x: x.strip(),
                filter(
                    bool,
                    text.replace('/auth', '').split(' ')
                )
            )
        except ValueError:
            self.sendMessage(chat_id, 'Ошибка в параметрах аутентификации')
            return
        result = self.parser.auth(login, password)
        if result:
            self.sendMessage(chat_id, 'Аутентификация установлена. Логин = {}'.format(login))
        else:
            self.sendMessage(chat_id, 'Ошибка аутентификации')

    def on_ko(self, chat_id, text, msg):
        self.send_ko(chat_id)

    def on_img(self, chat_id, text, msg):
        self.send_ko_img(chat_id)

    def on_pattern(self, chat_id, text, msg):
        text = text.replace('/pattern', '').strip()
        if 'standar' in text:
            self.set_data('code_pattern', None)
            self.sendMessage(chat_id, "Установлен стандартный шаблон кода")
        elif text:
            try:
                re.compile(text)
            except re.error:
                self.sendMessage(chat_id, "Шаблон кода не установлен")
                return

            self.set_data('code_pattern', text)
            self.sendMessage(chat_id, "Шаблон кода установлен: {}".format(text))
        else:
            if self.code_pattern:
                self.sendMessage(chat_id, "Шаблон кода: {}".format(self.code_pattern))
            else:
                self.sendMessage(chat_id, "Шаблон кода: стандартный")

    def on_link(self, chat_id, text, msg):
        data = self.get_data()
        text = text.replace('/link', '').strip()
        if text:
            self.set_data('link', text)
            self.sendMessage(chat_id, "Установлена ссылка {}".format(text))
        else:
            link = data.get('link')
            if link:
                self.sendMessage(chat_id, "Ссылка: {}".format(link))
            else:
                self.sendMessage(chat_id, "Настройки ссылки не найдено")

    def on_sleep_seconds(self, chat_id, text, msg):
        data = self.get_data()
        text = text.replace('/sleep_seconds', '').strip()
        if text:
            text = re.sub(r'\D', '', text)
            try:
                result = int(text)
            except (ValueError, TypeError):
                self.sendMessage(chat_id, "Ошибка в установке")
                return
            if not 10 <= result <= 300:
                self.sendMessage(chat_id, "Время sleep_seconds должно быть в итервале от 10 до 300 секунд. Если вы хотите выключить парсинг движка, воспользуйтесь командой /parse off")
            else:
                self.set_data('sleep_seconds', result)
                self.sendMessage(chat_id, "Установлена sleep_seconds = {}".format(text))
        else:
            self.sendMessage(chat_id, "sleep_seconds = {}".format(data.get('sleep_seconds')))

    def on_cord(self, chat_id, text, msg):
        if self.maps:
            cord_list = re.findall(CORD_RE, text)
            if len(cord_list) == 2:
                self.sendLocation(chat_id, *cord_list)

    def process_one_code(self, chat_id, code, message_id):
        try:
            self.parser.fetch(code)
        except GrabTimeoutError:
            self.sendMessage(chat_id, "Проблема подключения к движку")
            return
        parse_result = self.parser.parse()
        clock = parse_result.get('clock')

        server_message = parse_result.get('message', '').lower()

        code_ok = ('код принят' in server_message) or ('принят бонусный код' in server_message)
        code_old = ('вы уже ввели этот код' in server_message) or ('повторно отправить уже принятый' in server_message)
        code_bad = ('код не принят' in server_message) and not code_old
        new_level = 'выполняйте следующее задание' in server_message
        emoji = ''
        if code_ok:
            emoji = '✅ '
        elif code_old:
            emoji = '🔄 '
        elif code_bad:
            emoji = '❌ '
        if new_level:
            emoji += '💥 '

        metki_message = ""
        if code_ok and parse_result.get('new_metki'):
            metki = parse_result['new_metki']
            if len(metki) == 1:
                metki_message = "Сектор {sector_name}, метка {metka}".format(**metki[0])
            elif len(metki) <= 2:
                if metki[0]['sector_name'] == metki[1]['sector_name']:
                    metki_message = "Сектор {sector_name}, метка {metka1} или {metka2}".format(
                        sector_name=metki[0]['sector_name'], metka1=metki[0]['metka'], metka2=metki[1]['metka'])
                else:
                    metki_message = " или ".join("Сектор {sector_name}, метка {metka}".format(**metka) for metka in metki)
            if metki_message != "":
                metki_message = " {}.".format(metki_message)

        if server_message:
            self.sendMessage(chat_id, "{emoji}{code} : {server_message}.{metki_message}{clock}".format(
                emoji=emoji,
                clock=" Таймер: {}".format(clock) if clock else '',
                code=code,
                server_message=server_message,
                metki_message=metki_message,
            ), reply_to_message_id=message_id)

        self.parse_and_send(parse_result)

    def on_status(self, chat_id, text, msg):
        message = ''

        try:
            self.parser.fetch()
        except GrabTimeoutError:
            self.sendMessage(chat_id, "Проблема подключения к движку")
            return

        body = self.parser.g.doc.body.decode('cp1251')
        message += 'Движок {}\n'.format("включен" if 'игрок:' in body.lower() else 'выключен')
        message += 'Режим парсинга движка {}\n'.format("включен" if self.parse else "выключен")
        message += 'Режим ввода кодов {}\n'.format("включен" if self.type else "выключен")

        self.sendMessage(chat_id, message)

    def _on_chat_message(self, msg):
        text = msg.get('text')
        # Не отвечает на нетекстовые сообщения
        if not text:
            return

        chat_id = msg['chat']['id']
        # Не отвечает, если задан параметр settings.CHAT_ID и он не соответствует сообщению.
        if hasattr(settings, 'CHAT_ID') and chat_id != settings.CHAT_ID:
            return

        # парсинг сообщения на наличие команд.
        for pattern, method_str in self.routes:
            method = getattr(self, method_str, None)
            if method is not None and re.search(pattern, text):
                method(chat_id, text, msg)

        # парсинг сообщения на наличие кодов.
        if self.type and 2 < len(text) < 100:
            text = text.lower()
            if text[:2] == '/ ':
                text = text.replace('/ ', '')
                self.process_one_code(chat_id, text, msg.get('message_id'))
                return

            if self.code_pattern is None:
                code_pattern = STANDARD_CODE_PATTERN
                # конвертируем кириллицу в латинницу, если шаблон стандартный
                text = text.replace('д', 'd').replace('р', 'r')
            else:
                code_pattern = self.code_pattern

            if re.search(code_pattern, text, flags=re.I):
                for code in re.findall(code_pattern, text, flags=re.I):
                    if not 2 < len(code) < 100:
                        continue
                    if code_pattern == STANDARD_CODE_PATTERN and not ('d' in code and 'r' in code):
                        continue
                    self.process_one_code(chat_id, code, msg.get('message_id'))

    def on_chat_message(self, msg):
        if int(time.time()) - msg['date'] > 300:
            return
        logging.debug('new message')
        if self.sentry:
            try:
                self._on_chat_message(msg)
            except Exception as exc:
                self.sentry.captureException(exc_info=True)
        else:
            self._on_chat_message(msg)

    def send_ko(self, channel_id):
        for sector in self.parser.table_sector.all():
            sector['code_list'] = list(self.parser.table_code.find(sector_id=sector['id']))
            self.sendMessage(channel_id, sector_text(sector), parse_mode='Markdown')

    def send_ko_img(self, channel_id):
        for sector in self.parser.table_sector.all():
            ko_list = [x['ko'] for x in self.parser.table_code.find(sector_id=sector['id'])]
            ko_img = KoImg(ko_list=ko_list)
            self.sendPhoto(channel_id, ('ko.png', BytesIO(ko_img.content)))

    def get_data(self):
        return self.parser.table_bot.find_one(**{'token': settings.TOKEN})

    def handle_loop(self):
        if not self.parse:
            return
        try:
            self.parser.fetch()
        except GrabTimeoutError:
            return
        parse_result = self.parser.parse()
        self.parse_and_send(parse_result)

    def parse_and_send(self, parse_result):
        channel_id = getattr(settings, 'CHANNEL_ID', None)
        if channel_id is None:
            return

        if parse_result['new_level']:
            self.sendMessage(channel_id, 'Новый уровень')
            self.send_ko(channel_id)

            # Сбрасываем паттерн
            self.set_data('code_pattern', None)

        for tip in parse_result['tip_list']:
            self.sendMessage(channel_id, "Подсказка: {}".format(tip['text']))

        if parse_result['new_code']:
            self.send_ko(channel_id)

        if parse_result['new_spoiler']:
            self.sendMessage(channel_id, 'Открыт спойлер')


def __main__():
    for key in (
        'TOKEN',
        'DATASET',
    ):
        if not hasattr(settings, key):
            print('Заполните параметр {} в файле settings'.format(key))
            return
    bot = DzrBot(settings.TOKEN)
    bot.message_loop()
    while 1:
        bot.handle_loop()
        time.sleep(bot.sleep_seconds)


if __name__ == '__main__':
    __main__()
