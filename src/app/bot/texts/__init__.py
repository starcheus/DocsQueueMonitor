"""Centralized UI translations (uk / ru / en)."""

from __future__ import annotations

from typing import Any

SUPPORTED_LANGUAGES = ("uk", "ru", "en")
DEFAULT_LANGUAGE = "uk"

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "uk": {
        "start.welcome": (
            "Вітаю! Я незалежний бот моніторингу електронної черги "
            "зарубіжних центрів ДП «Документ».\n\n"
            "Я лише повідомляю про можливу появу вільних місць і даю "
            "посилання на офіційний сайт. Запис я не виконую."
        ),
        "start.choose_language": "Оберіть мову / Choose language / Выберите язык:",
        "menu.title": "Головне меню",
        "menu.choose_cities": "🔔 Обрати міста",
        "menu.my_subs": "📍 Мої підписки",
        "menu.status": "📊 Статус міст",
        "menu.language": "🌍 Мова",
        "menu.how": "ℹ️ Як це працює",
        "menu.privacy": "🔒 Конфіденційність",
        "menu.contact": "📩 Зв’язатися з розробником",
        "how.body": (
            "1. Оберіть країну та міста.\n"
            "2. Підпишіться на моніторинг.\n"
            "3. Отримайте сповіщення, якщо місця, ймовірно, з’явилися.\n"
            "4. Перейдіть на офіційний сайт і запишіться самостійно.\n\n"
            "Бот не гарантує наявність місця і не обходить захист сайту."
        ),
        "privacy.body": (
            "Ми зберігаємо лише Telegram ID, необов’язковий username/ім’я, "
            "мову, підписки та технічну історію сповіщень.\n\n"
            "Не збираємо паспортні дані, BankID, «Дію», телефони чи документи.\n\n"
            "Щоб видалити дані — натисніть кнопку нижче."
        ),
        "privacy.delete": "🗑 Видалити мої дані",
        "privacy.confirm": "Підтвердити видалення даних?",
        "privacy.confirm_yes": "Так, видалити",
        "privacy.confirm_no": "Скасувати",
        "privacy.deleted": "Ваші підписки деактивовано, профіль анонімізовано.",
        "disclaimer.short": (
            "Незалежний сервіс, не пов’язаний з ДП «Документ». "
            "Дані можуть запізнюватися. Запис — лише на офіційному сайті."
        ),
        "countries.title": "Оберіть країну:",
        "cities.title": "Оберіть міста ({country}):",
        "cities.subscribed": "Підписано: {city}",
        "cities.unsubscribed": "Відписано: {city}",
        "subs.empty": "У вас немає активних підписок.",
        "subs.title": "Ваші підписки:",
        "subs.item": "{city} — моніторинг увімкнено ✅",
        "subs.unsubscribe": "Відписатися: {city}",
        "subs.unsubscribe_all": "Відписатися від усіх",
        "subs.confirm_all": "Відписатися від усіх міст?",
        "subs.confirm_yes": "Так, відписатися",
        "subs.confirm_no": "Скасувати",
        "subs.all_removed": "Усі підписки вимкнено.",
        "status.title": "Статус обраних міст:",
        "status.item": (
            "{city}: {status}\n"
            "Перевірено: {checked}\n"
            "Останні місця: {available}"
        ),
        "status.empty": "Спочатку підпишіться на міста.",
        "status.unknown": "невідомо",
        "status.no_slots": "місць немає",
        "status.possibly_available": "ймовірно є місця",
        "status.available": "вільні місця",
        "status.error": "помилка перевірки",
        "status.disabled": "вимкнено",
        "notify.slots_available": (
            "🚨 Можливо, з’явилися вільні місця\n\n"
            "📍 {city}, {country}\n"
            "🕒 Перевірено: {checked_at}\n"
            "✅ Наявність підтверджено кількома перевірками\n\n"
            "Місця можуть швидко закінчитися. Перейдіть на офіційний сайт "
            "і перевірте доступність самостійно."
        ),
        "notify.btn_open_site": "🔗 Відкрити офіційний сайт",
        "notify.btn_unsubscribe": "🔕 Відписатися від {city}",
        "notify.btn_status": "📊 Перевірити статус",
        "contact.body": "Зв’язок з розробником: {contact}",
        "back": "⬅️ Назад",
        "done": "Готово",
    },
    "ru": {
        "start.welcome": (
            "Привет! Я независимый бот мониторинга электронной очереди "
            "зарубежных центров ГП «Документ».\n\n"
            "Я только сообщаю о возможном появлении мест и даю ссылку "
            "на официальный сайт. Запись я не выполняю."
        ),
        "start.choose_language": "Оберіть мову / Choose language / Выберите язык:",
        "menu.title": "Главное меню",
        "menu.choose_cities": "🔔 Выбрать города",
        "menu.my_subs": "📍 Мои подписки",
        "menu.status": "📊 Статус городов",
        "menu.language": "🌍 Язык",
        "menu.how": "ℹ️ Как это работает",
        "menu.privacy": "🔒 Конфиденциальность",
        "menu.contact": "📩 Связаться с разработчиком",
        "how.body": (
            "1. Выберите страну и города.\n"
            "2. Подпишитесь на мониторинг.\n"
            "3. Получите уведомление, если места, вероятно, появились.\n"
            "4. Перейдите на официальный сайт и запишитесь сами.\n\n"
            "Бот не гарантирует наличие места и не обходит защиту сайта."
        ),
        "privacy.body": (
            "Мы храним только Telegram ID, необязательный username/имя, "
            "язык, подписки и техническую историю уведомлений.\n\n"
            "Не собираем паспортные данные, BankID, «Дію», телефоны или документы.\n\n"
            "Чтобы удалить данные — нажмите кнопку ниже."
        ),
        "privacy.delete": "🗑 Удалить мои данные",
        "privacy.confirm": "Подтвердить удаление данных?",
        "privacy.confirm_yes": "Да, удалить",
        "privacy.confirm_no": "Отмена",
        "privacy.deleted": "Ваши подписки отключены, профиль анонимизирован.",
        "disclaimer.short": (
            "Независимый сервис, не связанный с ГП «Документ». "
            "Данные могут запаздывать. Запись — только на официальном сайте."
        ),
        "countries.title": "Выберите страну:",
        "cities.title": "Выберите города ({country}):",
        "cities.subscribed": "Подписано: {city}",
        "cities.unsubscribed": "Отписано: {city}",
        "subs.empty": "У вас нет активных подписок.",
        "subs.title": "Ваши подписки:",
        "subs.item": "{city} — мониторинг включён ✅",
        "subs.unsubscribe": "Отписаться: {city}",
        "subs.unsubscribe_all": "Отписаться от всех",
        "subs.confirm_all": "Отписаться от всех городов?",
        "subs.confirm_yes": "Да, отписаться",
        "subs.confirm_no": "Отмена",
        "subs.all_removed": "Все подписки отключены.",
        "status.title": "Статус выбранных городов:",
        "status.item": (
            "{city}: {status}\n"
            "Проверено: {checked}\n"
            "Последние места: {available}"
        ),
        "status.empty": "Сначала подпишитесь на города.",
        "status.unknown": "неизвестно",
        "status.no_slots": "мест нет",
        "status.possibly_available": "вероятно есть места",
        "status.available": "свободные места",
        "status.error": "ошибка проверки",
        "status.disabled": "отключено",
        "notify.slots_available": (
            "🚨 Возможно, появились свободные места\n\n"
            "📍 {city}, {country}\n"
            "🕒 Проверено: {checked_at}\n"
            "✅ Наличие подтверждено несколькими проверками\n\n"
            "Места могут быстро закончиться. Перейдите на официальный сайт "
            "и проверьте доступность самостоятельно."
        ),
        "notify.btn_open_site": "🔗 Открыть официальный сайт",
        "notify.btn_unsubscribe": "🔕 Отписаться от {city}",
        "notify.btn_status": "📊 Проверить статус",
        "contact.body": "Связь с разработчиком: {contact}",
        "back": "⬅️ Назад",
        "done": "Готово",
    },
    "en": {
        "start.welcome": (
            "Hi! I’m an independent bot that monitors foreign DP “Dokument” "
            "e-queue pages.\n\n"
            "I only notify about possible free slots and link to the official site. "
            "I never book appointments."
        ),
        "start.choose_language": "Оберіть мову / Choose language / Выберите язык:",
        "menu.title": "Main menu",
        "menu.choose_cities": "🔔 Choose cities",
        "menu.my_subs": "📍 My subscriptions",
        "menu.status": "📊 City status",
        "menu.language": "🌍 Language",
        "menu.how": "ℹ️ How it works",
        "menu.privacy": "🔒 Privacy",
        "menu.contact": "📩 Contact developer",
        "how.body": (
            "1. Choose a country and cities.\n"
            "2. Subscribe to monitoring.\n"
            "3. Get notified when slots may appear.\n"
            "4. Open the official site and book yourself.\n\n"
            "The bot does not guarantee availability and does not bypass site protections."
        ),
        "privacy.body": (
            "We store only Telegram ID, optional username/name, language, "
            "subscriptions, and technical notification history.\n\n"
            "We do not collect passport data, BankID, Diia, phone numbers, or documents.\n\n"
            "To delete your data, tap the button below."
        ),
        "privacy.delete": "🗑 Delete my data",
        "privacy.confirm": "Confirm data deletion?",
        "privacy.confirm_yes": "Yes, delete",
        "privacy.confirm_no": "Cancel",
        "privacy.deleted": "Your subscriptions were disabled and the profile anonymized.",
        "disclaimer.short": (
            "Independent service, not affiliated with DP “Dokument”. "
            "Data may be delayed. Booking is only on the official website."
        ),
        "countries.title": "Choose a country:",
        "cities.title": "Choose cities ({country}):",
        "cities.subscribed": "Subscribed: {city}",
        "cities.unsubscribed": "Unsubscribed: {city}",
        "subs.empty": "You have no active subscriptions.",
        "subs.title": "Your subscriptions:",
        "subs.item": "{city} — monitoring on ✅",
        "subs.unsubscribe": "Unsubscribe: {city}",
        "subs.unsubscribe_all": "Unsubscribe from all",
        "subs.confirm_all": "Unsubscribe from all cities?",
        "subs.confirm_yes": "Yes, unsubscribe",
        "subs.confirm_no": "Cancel",
        "subs.all_removed": "All subscriptions disabled.",
        "status.title": "Status of your cities:",
        "status.item": (
            "{city}: {status}\n"
            "Checked: {checked}\n"
            "Last available: {available}"
        ),
        "status.empty": "Subscribe to cities first.",
        "status.unknown": "unknown",
        "status.no_slots": "no slots",
        "status.possibly_available": "possibly available",
        "status.available": "free slots",
        "status.error": "check error",
        "status.disabled": "disabled",
        "notify.slots_available": (
            "🚨 Free slots may have appeared\n\n"
            "📍 {city}, {country}\n"
            "🕒 Checked: {checked_at}\n"
            "✅ Availability confirmed by multiple checks\n\n"
            "Slots can disappear quickly. Open the official site and verify yourself."
        ),
        "notify.btn_open_site": "🔗 Open official site",
        "notify.btn_unsubscribe": "🔕 Unsubscribe from {city}",
        "notify.btn_status": "📊 Check status",
        "contact.body": "Contact the developer: {contact}",
        "back": "⬅️ Back",
        "done": "Done",
    },
}


def resolve_language(telegram_language_code: str | None, stored: str | None = None) -> str:
    if stored in SUPPORTED_LANGUAGES:
        return stored
    if not telegram_language_code:
        return DEFAULT_LANGUAGE
    code = telegram_language_code.lower()
    if code.startswith("uk") or code.startswith("ua"):
        return "uk"
    if code.startswith("ru"):
        return "ru"
    if code.startswith("en"):
        return "en"
    return DEFAULT_LANGUAGE


def t(lang: str, key: str, **kwargs: Any) -> str:
    language = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    template = _TRANSLATIONS[language].get(key) or _TRANSLATIONS[DEFAULT_LANGUAGE].get(key) or key
    if kwargs:
        return template.format(**kwargs)
    return template
