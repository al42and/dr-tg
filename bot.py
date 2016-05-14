from telepot import Bot
import settings
import re
import time

from models import Parser, freq_dict, HELP_TEXT
from views import sector_text

CORD_RE = '([35]\d[\.,]\d+)'
STANDARD_CODE_PATTERN = '\d*[dд]\d*[rр]\d*'


class ManulaBot(Bot):
    freq = 28  # Частота рации
    parse = False  # Режим парсинга движка
    type = False  # Режим ввода кодов

    routes = (
        (CORD_RE, 'on_cord'),
            # (r'^/link', 'on_link'),
        (r'^/freq', 'on_freq'),
            # (CODE_RE, 'on_code'),
            # (r'^/auth', 'on_auth'),
        (r'^/help', 'on_help'),
        (r'^/type', 'on_type'),
        (r'^/parse', 'on_parse'),
        (r'^/cookie', 'on_cookie'),
        (r'^/pin', 'on_pin'),
        (r'^/pattern', 'on_pattern'),
    )

    def set_data(self, key, value):
        setattr(self, key, value)
        self.parser.db['bot'].upsert({
            'token': settings.TOKEN,
            key: value
        }, ['token'])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = Parser()

        self.parser.db['bot'].upsert({'token': settings.TOKEN}, ['token'])
        data = self.parser.db['bot'].find_one(**{'token': settings.TOKEN})
        for key in [
            'freq',
            'type',
            'parse',
        ]:
            value = data.get(key)
            if value is not None:
                setattr(self, key, value)

        cookie = data.get('cookie')
        if cookie:
            self.parser.set_cookie(cookie)

        pin = data.get('pin')
        if pin:
            self.parser.set_pin(pin)

        code_pattern = data.get('code_pattern')
        if code_pattern:
            self.code_pattern = code_pattern
        else:
            self.code_pattern = STANDARD_CODE_PATTERN

    def on_help(self, chat_id, text):
        self.sendMessage(chat_id, HELP_TEXT)

    def on_type(self, chat_id, text):
        if 'on' in text:
            self.set_data('type', True)
        elif 'off' in text:
            self.set_data('type', False)
        self.sendMessage(chat_id, "Режим ввода кодов: {}".format("Включен" if self.type else "Выключен"))

    def on_parse(self, chat_id, text):
        if 'on' in text:
            self.set_data('parse', True)
        elif 'off' in text:
            self.set_data('parse', False)
        self.sendMessage(chat_id, "Режим парсинга движка: {}".format("Включен" if self.parse else "Выключен"))

    def on_cookie(self, chat_id, text):
        for cookie in re.findall('(\w{24})', text):
            self.parser.set_cookie(cookie)
            self.set_data('cookie', cookie)
            self.sendMessage(chat_id, "Кука установлена")

    def on_pin(self, chat_id, text):
        text = text.replace('/pin', '').strip()
        self.parser.set_pin(text)
        self.set_data('pin', text)
        self.sendMessage(chat_id, "Пин установлен")

    def on_pattern(self, chat_id, text):
        text = text.replace('/pattern', '').strip()
        if 'standar' in text:
            text = STANDARD_CODE_PATTERN

        if text:
            try:
                re.compile(text)
            except re.error:
                self.sendMessage(chat_id, "Шаблон кода не установлен")

            self.set_data('code_pattern', text)
            self.sendMessage(chat_id, "Шаблон кода установлен: {}".format(text))
        else:
            self.sendMessage(chat_id, "Шаблон кода: {}".format(self.code_pattern))

    def on_link(self, chat_id, text):
        self.sendMessage(chat_id, 'Ссылка')

    def on_cord(self, chat_id, text):
        cord_list = re.findall(CORD_RE, text)
        if len(cord_list) == 2:
            self.sendLocation(chat_id, *cord_list)

    def on_code(self, chat_id, text):
        if not self.type:
            return
        code_list = re.findall(self.code_pattern, text, flags=re.I)

        for code in code_list:
            take_message = self.parser.take_code(code)
            if not take_message:
                continue
            message = "{} : {}".format(code, take_message)

            if 'Принят код' in take_message:
                # Если код принят, то парсим движок на принятые коды.
                parse_result = self.parser.parse()
                metka_list = []
                sector_list = parse_result['sector_list']
                for sector in sector_list:
                    for code in sector['code_list']:
                        metka_list.append(code['metka'])
                if metka_list:
                    message = "{} . Метка: {}".format(message, " или ".join(list(map(str, metka_list))))
            self.sendMessage(chat_id, message)

    def on_freq(self, chat_id, text):
        try:
            self.set_data('freq', int(text.replace('/freq', '')))
        except ValueError:
            pass
        freq_result = freq_dict.get(self.freq)
        if freq_result is None:
            self.sendMessage(chat_id, 'Используйте команду "/freq <число>" , где <число> - номер канала midland от 1 до 60.')
        else:
            self.sendMessage(chat_id, 'Основная частота: {} ||| Канал Midland: {}'.format(
                freq_result,
                str(self.freq),
            ))

    def on_auth(self, chat_id, text):
        try:
            login, password = map(
                lambda x: x.strip(),
                filter(
                    bool,
                    text.replace('/auth', '').split(' ')
                )
            )
        except ValueError:
            return
        self.parser.auth(login, password)
        self.sendMessage(chat_id, 'Авторизация установлена. Логин = {}'.format(login))

    def on_chat_message(self, msg):
        text = msg.get('text')
        if text is None:
            return
        chat_id = msg['chat'].get('id')

        # Отвечает не собеседнику, а в определенный чат, если в settings этот чат задан явно.
        if hasattr(settings, 'CHAT_ID'):
            chat_id = settings.CHAT_ID

        for pattern, method_str in self.routes:
            method = getattr(self, method_str, None)
            if method is not None and re.search(pattern, text):
                method(chat_id, text)

        if re.search(self.code_pattern, text, flags=re.I):
            self.on_code(chat_id, text)

    def handle_loop(self):
        if not self.parse:
            return
        channel_id = getattr(settings, 'CHANNEL_ID', None)
        if channel_id is None:
            return

        self.parser.fetch()
        parse_result = self.parser.parse()
        if parse_result['new_level']:
            self.sendMessage(channel_id, 'Новый уровень.')
        for tip in parse_result['tip_list']:
            self.sendMessage(channel_id, "Подсказка: {}".format(tip['text']))

        if parse_result['new_code']:
            for sector in self.parser.table_sector.all():
                sector['code_list'] = list(self.parser.table_code.find(sector_id=sector['id']))
                self.sendMessage(channel_id, sector_text(sector), parse_mode='Markdown')


if __name__ == '__main__':
    bot = ManulaBot(settings.TOKEN)
    bot.message_loop()
    while 1:
        bot.handle_loop()
        time.sleep(getattr(settings, 'SLEEP_SECONDS', 10))
