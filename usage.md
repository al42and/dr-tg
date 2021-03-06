# Использование бота

## Файл settings.py

Создайте файл с именем `settings.py` рядом с файлом `settings.example.py`. 
В этом файле хранятся базовые настройки бота, которые нужны только для запуска бота.
Остальные настройки можно задавать после запуска.

* `TOKEN` . телеграм-токен, получаемый у мета-бота @botfather
* `DATASET` - расположение базы. Имеет вид `<движок_базы>://<логин>@<пароль>@<хост>:<порт>/<название_базы>`
* `CHANNEL_ID` - ID канала (или чата), куда бот отправляет сообщения о кодах (табличкой), подсказках, новых уровнях.
В случае отсутствия настройки, бот не будет посылать сообщения об обновлениях.
* `CHAT_ID` - ID чата, в котором бот принимает команды-сообщения и коды.
В случае отсутствия настройки, бот будет слушать всех.
 
### Зачем нужны `CHAT_ID` и `CHANNEL_ID`?

`CHAT_ID` может отсутствовать. В этом случае бот будет слушать всех (в том числе в личке).
Если вы хотите, чтобы бот принимал сообщения только из определенного чата, заполните идентификатор `CHAT_ID`.
Для того, чтобы узнать идентификатор чата, запустите бота с пустым `CHAT_ID` и введите команду `/get_chat_id` в нужном чате. 
В ответе бот напишет идентификатор.

`CHANNEL_ID` и `CHAT_ID` могут совпадать, и тогда бот будет все сообщения писать только в одном месте. 
Однако на практике, легко видеть,
что сообщения с табличкой КО могут быть очень большими, и бот может засорять пространство основного чата. В этом случае удобно выделить боту
 телеграм-канал, где только он будет писать сообщения о происходящем в движке.
  
## Пробитие кодов
Бот читает общий чат, забирает оттуда коды, найденные по шаблону (регулярному выражению), пробивает в движок.

При этом не требуется указывать боту никакие дополнительные команды, и например, 
на сообщение "Нашел код dr451 или dr457, плохо видно" бот пробьет оба кода "dr451" и "dr457".

Бот пробивает коды только если настройка `/type` включена. 
Вы можете выключить автоматическое пробитие кодов командой `/type off`, например, если на уровне есть ложные коды.

Можно устанавливать шаблон поиска кода по [регулярному выражению](https://ru.wikipedia.org/wiki/%D0%A0%D0%B5%D0%B3%D1%83%D0%BB%D1%8F%D1%80%D0%BD%D1%8B%D0%B5_%D0%B2%D1%8B%D1%80%D0%B0%D0%B6%D0%B5%D0%BD%D0%B8%D1%8F).
Например, если коды на уровне представляют собой слово и две цифры ( "код34" , "слово68" ) , 
то можно задать такую регулярку: `/pattern \w+\d{2}`. Подробнее о том, как составлять регулярные выражения можно почитать на вики.

Если вы хотите вернуть стандартный шаблон, введите `/pattern standard` - это настройка применит стандартный шаблон дозоровских кодов.
При стандартном шаблоне, кириллические буквы "д" и "р" также рассматриваются ботом как части кода, поэтому писать сообщения можно не переключая
  раскладку на латинскую клавиатуру. То есть при стандартном шаблоне сообщение из сообщения "код д4р" будет выделен код `d4r`.
    
Также есть возможность пробить любой код без поиска по шаблону и без каких-либо замен букв. Для этого нужно ввести слэш, пробел и код.
Слэш удобно набирать в телефоне, так как все telegram-приложения содержат его на экранной клавиатуре. Например, из сообщения
`/ пробей1код2именно3такой4не5спрашивай` будет взят код `пробей1код2именно3такой4не5спрашивай` без каких либо проверок на шаблон и без каких-либо замен символов. 

После пробития кода в движок, бот возвращается в чат и пишет сообщение, полученное от движка. Примеры ответа от движка:

* "Код принят. Ищите следующий составной код" 
* "Код не принят. Проверьте правильность кода"
* "Код не принят. Вы уже вводили тот код"

## Безопасность

Бот не предлагает никакой своей авторизации, а делегирует эту задачу администраторам чата. 
Это означает, что боту будет слушать всех людей в чате с идентификатором `CHAT_ID`. 
Вот несколько советов для того, чтобы обезопасить бота от посторонних глаз.
 
* Следите за составом группы (чата), где бот принимает команды
* Если используете канал, проверьте, что он приватный. Следите за составом канала.
* Используйте для бота отдельный аккаунт в дозорном движке.
* Никому не сообщайте параметр `TOKEN_ID`

## Аутентификация в дозорном движке

Аутентификация осуществляется по логин-паролю.
 
Логин-пароль - соответствуют определенному аккаунту. Задаются боту так: `/auth login parol`.

Если по каким-то причинам для бота нет отдельного аккаунта, и вы хотите использовать один аккаунт в браузере и в боте одновременно,
то могут возникнуть проблемы при аутентификации: движок будет сбрасывать
предыдущую cookie и устанавливать новую, то есть по движок предлагает быть аутентифицированным только с одного устройства.

Это, однако, можно легко обойти, если поставить на обоих устройствах одинаковую cookie. 
Если вы сможете добыть cookie из браузера dozorSiteSession, то установите ее для бота при помощи команды так 
`/cookie KTerByfGopF5dSgFjkl07x8v`. Используйте эту команду, если вы понимаете, что делаете. 

Если вы прошли аутентификацию через команду `/auth`, то использовать команду `/cookie` не надо.

## Парсинг координат

Если бот видит в сообщение нечто, похожее на координаты, он посылает в чат особое location-сообщение.

## Команды
* `/cookie` - установка аутентификационной cookie.
* `/auth` - аутентификация по логину-паролю
* `/help` - сообщение со списком команд бота
* `/ko` - таблица КО в виде текста
* `/img` - таблица КО в виде картинки
* `/link` - вывод "ссылки", где "ссылка" - любой текст. `/link example` - сохраняет текст "example" в качестве "ссылки". Удобно для хранения сылки на гугл-док или движок.
* `/get_chat_id` - вывод идентификатора текущего чата
* `/parse` - boolean параметр "парсинг движка". Отключается так `/parse off` и включается так `/parse on`   
* `/pattern` - шаблон кода. Подробнее про это в разделе "Пробитие кодов"
* `/sleep_seconds` - периодичность парсинга движка. от 10 до 300 секунд. По умолчанию - 30 секунд.   
* `/status` - вывод актуальных настроек бота, а также статусе подключения к движку.
* `/type` - boolean параметр "ввод кодов". Отключается так `/type off` и включается так `/type on`
