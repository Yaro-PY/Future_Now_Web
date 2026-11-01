"""Stable callback keys and Ukrainian/English labels for the supplied User Flow."""

def pairs(*items):
    return {key: (uk, en) for key, uk, en in items}

TYPES = pairs(
    ('international', 'Міжнародні проєкти', 'International projects'),
    ('ukrainian', 'Українські проєкти', 'Ukrainian projects'),
    ('exchange', 'Обміни', 'Exchanges'), ('course', 'Курси', 'Courses'),
    ('program', 'Освітні програми', 'Educational programs'),
    ('volunteer', 'Волонтерство', 'Volunteering'), ('grant', 'Гранти', 'Grants'),
    ('contest', 'Конкурси', 'Competitions'), ('internship', 'Стажування', 'Internships'),
    ('hackathon', 'Хакатони', 'Hackathons'), ('other', 'Інше', 'Other'),
    ('any', 'Усі можливості', 'All opportunities'))
TOPICS = pairs(
    ('it', 'ІТ', 'IT'), ('business', 'Бізнес', 'Business'),
    ('leadership', 'Лідерство', 'Leadership'), ('art', 'Мистецтво', 'Art'),
    ('media', 'Медіа', 'Media'), ('education', 'Освіта', 'Education'),
    ('volunteer', 'Волонтерство', 'Volunteering'), ('ecology', 'Екологія', 'Ecology'),
    ('sport', 'Спорт', 'Sport'), ('culture', 'Культура', 'Culture'),
    ('international', 'Міжнародні відносини', 'International relations'),
    ('other', 'Інше', 'Other'))
AGES = pairs(('13-16', '13–16', '13–16'), ('16-18', '16–18', '16–18'),
             ('18+', '18 і більше', '18 and over'), ('any', 'Будь-який', 'Any age'))
COUNTRIES = pairs(('ukraine', 'Україна', 'Ukraine'), ('europe', 'Європа', 'Europe'),
                  ('other', 'Інші країни', 'Other countries'),
                  ('international', 'Міжнародна', 'International'),
                  ('online', 'Онлайн', 'Online'), ('any', 'Усі варіанти', 'All locations'))
CITIES = pairs(('ivanofrankivsk', 'Івано-Франківськ', 'Ivano-Frankivsk'),
              ('lviv', 'Львів', 'Lviv'), ('kyiv', 'Київ', 'Kyiv'),
              ('uzhhorod', 'Ужгород', 'Uzhhorod'), ('odesa', 'Одеса', 'Odesa'),
              ('kharkiv', 'Харків', 'Kharkiv'), ('poltava', 'Полтава', 'Poltava'),
              ('other', 'Інше', 'Other'), ('any', 'Уся Україна', 'All Ukraine'))
FORMATS = pairs(('online', 'Онлайн', 'Online'), ('offline', 'Офлайн', 'In person'),
                ('hybrid', 'Змішаний', 'Hybrid'), ('any', 'Не має значення', 'Any format'))
DATES = pairs(('nearest', 'Найближчі 7 днів', 'Next 7 days'),
              ('month', 'Цього місяця', 'This month'),
              ('next_month', 'Наступного місяця', 'Next month'),
              ('any', 'Без обмежень', 'No restrictions'))
BENEFITS = pairs(('free', 'Безкоштовно', 'Free'), ('funded', 'Є фінансування', 'Funding'),
                 ('travel', 'Покриття подорожі', 'Travel covered'),
                 ('housing', 'Проживання', 'Accommodation'), ('meals', 'Харчування', 'Meals'),
                 ('transport', 'Проїзд', 'Transport'), ('certificate', 'Сертифікат', 'Certificate'))
CRITERIA = pairs(('free', 'Безкоштовно', 'Free'),
                 ('funded', 'З фінансуванням', 'With funding'),
                 ('paid', 'Потрібна оплата', 'Payment required'),
                 ('travel', 'Поїздка', 'Trip'))
BENEFITS.update(CRITERIA)
FIELDS = pairs(('age', 'Вік', 'Age'), ('country', 'Країна / регіон', 'Country / region'),
               ('city', 'Область / місто', 'Region / city'), ('topics', 'Цікаві напрями', 'Interests'),
               ('format', 'Формат участі', 'Participation format'),
               ('criteria', 'Додаткові критерії', 'Additional criteria'),
               ('type', 'Тип можливості', 'Opportunity type'), ('date', 'Дата / дедлайн', 'Date / deadline'))
CATALOGS = {'type': TYPES, 'topics': TOPICS, 'age': AGES, 'country': COUNTRIES,
            'city': CITIES, 'format': FORMATS, 'date': DATES, 'criteria': CRITERIA}

TEXT = pairs(
    ('welcome', 'Вітаємо в User Flow!\nЗнаходь проєкти, навчання, гранти та інші можливості за своїми інтересами.', 'Welcome to User Flow!\nFind projects, learning, grants and other opportunities that match your interests.'),
    ('language', 'Оберіть мову / Choose language', 'Оберіть мову / Choose language'),
    ('menu', 'Головне меню', 'Main menu'), ('search', 'Знайти можливість', 'Find opportunities'),
    ('saved', 'Збережені', 'Saved'), ('profile', 'Мій профіль', 'My profile'),
    ('about', 'Про бота', 'About the bot'), ('settings', 'Налаштування', 'Settings'),
    ('back', 'Назад', 'Back'), ('cancel', 'Скасувати', 'Cancel'), ('next', 'Далі', 'Next'),
    ('done', 'Готово', 'Done'), ('save', 'Зберегти', 'Save'), ('remove', 'Видалити', 'Remove'),
    ('details', 'Детальніше', 'Details'), ('edit', 'Редагувати', 'Edit'),
    ('filters', 'Змінити фільтри', 'Change filters'), ('new_search', 'Новий пошук', 'New search'),
    ('search_go', 'Пошук', 'Search'), ('all_topics', 'Усі тематики', 'All topics'),
    ('no_criteria', 'Не має значення', 'No preferences'),
    ('pick', 'Оберіть:', 'Choose:'), ('age_prompt', 'Вкажіть свій вік (10–100) кнопкою або повідомленням:', 'Choose your age (10–100) or type it:'),
    ('invalid_age', 'Введіть ціле число від 10 до 100.', 'Enter a whole number from 10 to 100.'),
    ('review', 'Перевірте профіль і збережіть.', 'Review and save your profile.'),
    ('profile_saved', 'Зміни збережено', 'Changes saved'),
    ('no_profile', 'Спочатку створіть профіль.', 'Create your profile first.'),
    ('no_results', 'На жаль, за такими критеріями можливостей не знайдено. Спробуйте змінити фільтри.', 'No opportunities match these criteria. Try changing the filters.'),
    ('results', 'Список результатів', 'Search results'), ('page', 'Сторінка', 'Page'),
    ('empty_saved', 'Ви ще не зберігали можливості.', 'You have not saved any opportunities yet.'),
    ('saved_ok', 'Можливість збережено', 'Opportunity saved'),
    ('already_saved', 'Ця можливість уже у збережених.', 'This opportunity is already saved.'),
    ('removed', 'Можливість видалено зі збережених.', 'Opportunity removed from saved.'),
    ('unknown', 'Не вказано', 'Not specified'), ('free', 'Безкоштовно', 'Free'),
    ('paid', 'Платно', 'Paid'), ('deadline', 'Дедлайн', 'Deadline'), ('start_date', 'Дата проведення', 'Event date'),
    ('status', 'Статус', 'Status'), ('open', 'Актуальна за відомими датами', 'Open according to known dates'),
    ('expired', 'Дедлайн минув / можливість завершена', 'Deadline passed / opportunity ended'),
    ('check_source', 'Дати не вказані — перевірте першоджерело', 'Dates unknown — check the source'),
    ('self_paced', 'Навчання у власному темпі', 'Self-paced learning'),
    ('verified_at', 'Перевірено джерело', 'Source checked'),
    ('any_age', 'Без вікових обмежень', 'No age restriction'),
    ('organizer', 'Організатор', 'Organizer'), ('price', 'Вартість', 'Price'),
    ('requirements', 'Вимоги', 'Requirements'), ('benefits', 'Що покривається', 'Benefits'),
    ('event_language', 'Мова участі', 'Participation language'),
    ('registration', 'Перейти до реєстрації', 'Go to registration'), ('share', 'Поділитися', 'Share'),
    ('subscribe', 'Підписатися на дедлайн', 'Subscribe to deadline'),
    ('unsubscribe', 'Відписатися від дедлайну', 'Unsubscribe from deadline'),
    ('subscribed', 'Підписку збережено. Увімкніть дедлайни в налаштуваннях сповіщень.', 'Subscription saved. Enable deadline notifications in settings.'),
    ('unsubscribed', 'Підписку скасовано.', 'Subscription removed.'),
    ('unavailable', 'Посилання недоступне. Можна повідомити про проблему.', 'The link is unavailable. You can report a problem.'),
    ('no_url', 'Посилання відсутнє.', 'No link is available.'),
    ('open_link', 'Відкрити посилання', 'Open link'),
    ('retry', 'Спробувати ще', 'Try again'), ('report', 'Повідомити про проблему', 'Report a problem'),
    ('report_pick', 'Виберіть тип проблеми:', 'Choose the problem type:'),
    ('bad_info', 'Неправильна інформація', 'Incorrect information'),
    ('bad_link', 'Неправильне посилання', 'Incorrect link'), ('broken_link', 'Неробоче посилання', 'Broken link'),
    ('ended', 'Можливість завершилася', 'Opportunity ended'), ('other', 'Інше', 'Other'),
    ('report_text', 'Опишіть проблему повідомленням (до 2000 символів).', 'Describe the problem in a message (up to 2000 characters).'),
    ('send', 'Надіслати', 'Send'), ('report_thanks', 'Дякуємо! Ваше повідомлення збережено для розгляду.', 'Thank you! Your report has been saved for review.'),
    ('error', 'Щось пішло не так. Спробуйте ще раз.', 'Something went wrong. Please try again.'),
    ('stale', 'Ця кнопка застаріла. Скористайтеся останнім повідомленням або /menu.', 'This button is outdated. Use the latest message or /menu.'),
    ('notifications', 'Сповіщення', 'Notifications'), ('search_settings', 'Пошукові налаштування', 'Search settings'),
    ('help', 'Допомога', 'Help'), ('on', 'Увімкнено', 'On'), ('off', 'Вимкнено', 'Off'),
    ('new_notifications', 'Нові можливості', 'New opportunities'),
    ('deadline_notifications', 'Дедлайни', 'Deadlines'), ('topic_notifications', 'Обрані напрями', 'Selected interests'),
    ('notifications_info', 'Перевірка щогодини. Дедлайни — за 3 дні для збережених / підписаних можливостей. Нові можливості — за профілем; «Обрані напрями» вмикає відбір за інтересами.', 'Checked hourly. Deadline reminders within 3 days for saved / subscribed opportunities. New opportunities follow your profile; selected interests enables topic filtering.'),
    ('help_text', 'Пошук: оберіть фільтри й натисніть «Пошук».\nЗбереження: натисніть «Зберегти» у картці.\nФільтри: «Змінити фільтри» у результатах.\nМова та сповіщення: у налаштуваннях.\nПроблема: «Повідомити про проблему».\n/menu — головне меню, /cancel — скасувати дію.', 'Search: choose filters and press Search.\nSave: press Save on an opportunity.\nFilters: Change filters in results.\nLanguage and notifications: in settings.\nProblems: Report a problem.\n/menu — main menu, /cancel — cancel the current action.'),
    ('about_text', 'User Flow допомагає молоді знаходити проєкти, курси, обміни, освітні програми, волонтерство, гранти, конкурси та стажування.\n\n1. Оберіть критерії.\n2. Перегляньте результати.\n3. Відкрийте деталі.\n4. Збережіть або перейдіть до реєстрації.\n\nДжерело: МАН України та додані адміністратором матеріали. Невідомі дані позначені явно. Умови й доступність перевіряйте в організатора.', 'User Flow helps young people find projects, courses, exchanges, educational programs, volunteering, grants, competitions and internships.\n\n1. Choose criteria.\n2. Browse results.\n3. Open details.\n4. Save or go to registration.\n\nSources: Junior Academy of Sciences of Ukraine and material imported by the administrator. Unknown data is labelled. Check terms and availability with the organizer.'),
    ('new_digest', 'Нові можливості за вашим профілем', 'New opportunities matching your profile'),
    ('deadline_reminder', 'Наближається дедлайн', 'Deadline approaching'),
    ('notice_saved', 'Налаштування збережено', 'Settings saved'),
    ('text_hint', 'Скористайтеся кнопками або /menu.', 'Use the buttons or /menu.'),
    ('report_invalid', 'Повідомлення має містити 1–2000 символів.', 'The message must contain 1–2000 characters.'))

def tr(key, language='uk'):
    return TEXT[key][language == 'en']

def label(catalog, key, language='uk'):
    return catalog.get(str(key), (str(key), str(key)))[language == 'en']

# Updated product wording and proposal/moderation screens.
FIELDS.update(pairs(('title', 'Назва', 'Title'), ('url', 'Посилання', 'Link'),
                    ('description', 'Опис та організатор', 'Description and organizer'),
                    ('deadline', 'Дедлайн', 'Deadline'), ('topics', 'Теги оголошення', 'Opportunity tags')))
TEXT.update(pairs(
    ('withdrawn', 'Відкликана', 'Withdrawn'),
    ('withdraw_proposal', 'Відкликати пропозицію', 'Withdraw proposal'),
    ('withdraw_warning', 'Пропозицію буде відкликано з черги перевірки. Опублікувати її після цього не можна.', 'This proposal will leave the review queue and cannot be published afterwards.'),
    ('proposal_withdrawn', 'Пропозицію відкликано.', 'Proposal withdrawn.'),
    ('proposal_not_pending', 'Пропозицію вже опрацьовано або відкликано. Зміни недоступні.', 'This proposal has been reviewed or withdrawn. Changes are unavailable.'),
    ('edit_conflict', 'Запис уже змінено. Чернетку збережено на цьому екрані; відкрийте пропозицію знову, щоб завантажити актуальну версію.', 'This record has changed. Your draft remains on this screen; reopen the proposal to load the latest version.'),
    ('not_found', 'Запис не знайдено.', 'Record not found.'),
    ('recover_access', 'Відновити доступ', 'Recover access'),
    ('recovery_info', 'Ви підтвердили себе через Telegram. Тут можна задати новий пароль лише для профілю, привʼязаного до цього Telegram. Старий пароль не потрібен; усі сесії сайту буде завершено.', 'Telegram has verified you. You can set a new password only for the profile linked to this Telegram account. The old password is not required; all website sessions will be signed out.'),
    ('recovery_unlinked', 'До цього Telegram ще не привʼязано логін сайту. Якщо ви маєте доступ до акаунта, спочатку привʼяжіть його через /login. Відновити непривʼязаний акаунт лише за ніком неможливо.', 'No website login is linked to this Telegram yet. If you can sign in, link your account using /login first. An unlinked account cannot be recovered by nickname alone.'),
    ('delete_account', 'Видалити профіль', 'Delete profile'),
    ('delete_warning', 'Це назавжди видалить спільний профіль сайту й бота: пароль, фільтри, обране, підписки, пропозиції та скарги. Сесії буде завершено. Опубліковані оголошення залишаться в каталозі без привʼязки до вашого профілю.', 'This permanently deletes your shared website and bot profile: password, filters, favorites, subscriptions, proposals and reports. Sessions will end. Published listings will remain in the catalog without a link to your profile.'),
    ('delete_prompt', 'Для підтвердження надішліть свій нік, а потім натисніть «Видалити профіль»:', 'To confirm, send your nickname and then press Delete profile:'),
    ('delete_confirmation', 'Введіть свій нік точно як у профілі.', 'Type your nickname exactly as shown in your profile.'),
    ('account_deleted', 'Спільний профіль видалено, сесії сайту завершено. Щоб почати знову, надішліть /start.', 'Your shared profile was deleted and website sessions ended. Send /start to begin again.'),
    ('saved', 'Обране', 'Favorites'), ('save', '⭐ В обране', '⭐ Add to favorites'),
    ('save_changes', 'Зберегти зміни', 'Save changes'),
    ('empty_saved', 'В обраному поки немає можливостей.', 'Your favorites list is empty.'),
    ('saved_ok', 'Додано в обране', 'Added to favorites'),
    ('already_saved', 'Ця можливість уже в обраному.', 'This opportunity is already in favorites.'),
    ('removed', 'Видалено з обраного.', 'Removed from favorites.'),
    ('start_profile', 'Створити профіль і почати', 'Create profile and start'),
    ('later', 'Ознайомитися пізніше', 'Continue later'),
    ('tags', 'Теги', 'Tags'),
    ('expiry_notifications', 'Завершення обраних можливостей', 'Expired favorites'),
    ('favorite_expired', 'Обрана можливість уже завершилася', 'A favorite opportunity has ended'),
    ('notifications_info', 'Перевірка щогодини. Нові можливості — за профілем. Дедлайни — за 3 дні для обраних / підписаних. Про завершення обраної можливості повідомляємо один раз; ці сповіщення можна вимкнути.', 'Checked hourly. New opportunities follow your profile. Deadline reminders within 3 days for favorites / subscriptions. An expired favorite is reported once; these notifications can be disabled.'),
    ('proposal', 'Запропонувати можливість', 'Suggest an opportunity'),
    ('my_proposals', 'Мої пропозиції', 'My suggestions'),
    ('moderation', 'Перевірити пропозиції', 'Review suggestions'),
    ('proposal_intro', 'Поділіться можливістю для інших! Назва, посилання, опис і теги потраплять на перевірку адміністратору. До схвалення оголошення не зʼявиться в пошуку. Ліміт: 3 подання на добу, до 3 у черзі, інтервал 10 хвилин.', 'Share an opportunity! Its title, link, description and tags will be reviewed by an administrator. It will appear in search only after approval. Limit: 3 submissions per day, up to 3 pending, 10 minutes between submissions.'),
    ('proposal_begin', 'Заповнити пропозицію', 'Create suggestion'),
    ('proposal_title', 'Введіть назву можливості (8–150 символів).', 'Enter the opportunity title (8–150 characters).'),
    ('proposal_url', 'Надішліть публічне посилання https:// або http:// на першоджерело.', 'Send a public https:// or http:// link to the original source.'),
    ('proposal_description', 'Опишіть можливість, організатора та умови участі (40–1500 символів).', 'Describe the opportunity, organizer and eligibility (40–1500 characters).'),
    ('proposal_deadline', 'Вкажіть дедлайн у форматі ДД.ММ.РРРР або РРРР-ММ-ДД. Якщо він невідомий, натисніть «Не вказано».', 'Enter the deadline as DD.MM.YYYY or YYYY-MM-DD. If unknown, press Not specified.'),
    ('proposal_age', 'Оберіть вікову групу або напишіть точні межі, наприклад 13–30. Невідомі обмеження позначте «Не вказано».', 'Choose an age group or enter exact bounds, e.g. 13–30. Use Not specified for unknown restrictions.'),
    ('proposal_review', 'Перевірте дані. Після надсилання пропозиція піде на модерацію.', 'Review the information. Submitting sends it to moderation.'),
    ('proposal_sent', 'Дякуємо! Пропозицію надіслано на перевірку. Статус доступний у «Мої пропозиції».', 'Thank you! Your suggestion is awaiting review. Track its status in My suggestions.'),
    ('proposal_invalid', 'Перевірте формат і довжину введених даних.', 'Check the format and length of the information.'),
    ('proposal_bad_url', 'Потрібне публічне посилання на сайт без логіна й пароля. Локальні адреси не приймаються.', 'A public website link without a username or password is required. Local addresses are not accepted.'),
    ('proposal_bad_deadline', 'Введіть справжню майбутню дату у вказаному форматі або оберіть «Не вказано».', 'Enter a valid future date in the specified format or select Not specified.'),
    ('proposal_limit', 'Ліміт подань вичерпано: 3 на добу або 3 в черзі. Спробуйте пізніше.', 'Submission limit reached: 3 per day or 3 pending. Try again later.'),
    ('proposal_cooldown', 'Між поданнями має пройти 10 хвилин.', 'Wait 10 minutes between submissions.'),
    ('proposal_duplicate', 'Це посилання вже є в базі або серед поданих пропозицій.', 'This link is already in the database or submitted suggestions.'),
    ('proposal_unconfigured', 'Приймання пропозицій тимчасово недоступне: адміністратор ще не налаштований.', 'Suggestions are temporarily unavailable: no administrator is configured.'),
    ('pending', 'На перевірці', 'Awaiting review'), ('approved', 'Схвалено', 'Approved'),
    ('rejected', 'Відхилено', 'Rejected'),
    ('proposal_approved', 'Вашу пропозицію схвалено', 'Your suggestion was approved'),
    ('proposal_rejected', 'Вашу пропозицію відхилено', 'Your suggestion was rejected'),
    ('empty_proposals', 'Пропозицій поки немає.', 'No suggestions yet.'),
    ('approve', 'Схвалити й опублікувати', 'Approve and publish'),
    ('reject', 'Відхилити', 'Reject'), ('edit_proposal', 'Уточнити дані', 'Edit information'),
    ('moderation_reason', 'Напишіть причину відхилення (5–500 символів). Вона буде видима автору.', 'Enter a rejection reason (5–500 characters). The author will see it.'),
    ('moderation_done', 'Рішення збережено.', 'Decision saved.'),
    ('moderation_changed', 'Цю пропозицію вже розглянуто. Оновіть чергу.', 'This suggestion was already reviewed. Refresh the queue.'),
    ('moderation_link', 'Не вдалося перевірити посилання. Оголошення не опубліковано: перевірте першоджерело та спробуйте ще раз.', 'The link could not be verified. The suggestion was not published: check the original source and try again.'),
    ('reason', 'Причина', 'Reason'),
    ('about_text', 'Цей бот допомагає знаходити навчання, проєкти, обміни, гранти, волонтерство та стажування. Він підійде, якщо ви шукаєте можливості для розвитку й хочете повернутися до цікавого оголошення пізніше.\n\nЯк користуватися:\n1. Створіть профіль.\n2. Оберіть критерії пошуку.\n3. Перегляньте оголошення та їхні теги.\n4. Додайте цікаве в обране або перейдіть до реєстрації.\n\nМожна також запропонувати власну можливість — її перевірить адміністратор. Бот не реєструє вас автоматично. Умови, актуальність і витрати уточнюйте в організатора; невідомі дані позначено явно.', 'This bot helps you find learning, projects, exchanges, grants, volunteering and internships. It is useful when you want development opportunities and a way to revisit an interesting listing later.\n\nHow it works:\n1. Create a profile.\n2. Choose search criteria.\n3. Browse opportunities and their tags.\n4. Add favorites or go to registration.\n\nYou can suggest your own opportunity for administrator review. The bot does not register you automatically. Check terms, availability and costs with the organizer; unknown information is labelled.'),
    ('help_text', 'Пошук: оберіть критерії й натисніть «Пошук». Тематики показані тегами в оголошеннях.\nОбране: натисніть «В обране» в картці. Завершені можливості позначено; сповіщення можна налаштувати.\nВласне оголошення: «Запропонувати можливість» → заповніть форму → надішліть на перевірку.\nМова й сповіщення: у налаштуваннях.\n/about — про бота, /menu — меню, /cancel — скасувати дію.', 'Search: choose criteria and press Search. Topics are shown as opportunity tags.\nFavorites: press Add to favorites on a listing. Expired opportunities are labelled; notifications can be configured.\nYour listing: Suggest an opportunity → fill out the form → submit for review.\nLanguage and notifications: in settings.\n/about — about the bot, /menu — menu, /cancel — cancel.')
))

TEXT.update(pairs(('no_tags', 'Без тегів', 'No tags'), ('submission_expired', 'Дедлайн пропозиції вже минув. Відхиліть її або уточніть дату перед публікацією.', 'The suggestion deadline has passed. Reject it or correct the date before publication.')))

FIELDS.update(pairs(('nickname', 'Логін / нік', 'Login / nickname'),
                    ('display_name', 'Імʼя', 'Name')))
TEXT.update(pairs(
    ('nickname_prompt', 'Оберіть нік, наприклад yaro_ua. 3–32 латинські літери, цифри або _; почніть із літери. Регістр не має значення.', 'Choose a nickname, e.g. yaro_ua. Use 3–32 Latin letters, digits or _; start with a letter. Case does not matter.'),
    ('name_prompt', 'Як до вас звертатися? Введіть імʼя (2–80 символів).', 'What should we call you? Enter your name (2–80 characters).'),
    ('nickname_invalid', 'Нік має містити 3–32 латинські літери, цифри або _ та починатися з літери.', 'Use 3–32 Latin letters, digits or _ and start with a letter.'),
    ('nickname_taken', 'Цей нік уже зайнятий. Оберіть інший.', 'This nickname is already taken. Choose another.'),
    ('name_invalid', 'Введіть імʼя довжиною 2–80 символів без керувальних символів.', 'Enter a name of 2–80 characters without control characters.'),
    ('age_prompt', 'Оберіть свою вікову групу: 13–16, 16–18 або 18 і більше. Можна також написати свій вік (13–100).', 'Choose your age group: 13–16, 16–18, or 18 and over. You can also type your age (13–100).'),
    ('invalid_age', 'Оберіть вікову групу або введіть ціле число від 13 до 100.', 'Choose an age group or enter a whole number from 13 to 100.')
))

TEXT.update(pairs(
    ('welcome', 'Вітаємо у Future Now! Знаходьте навчання, проєкти та інші можливості.', 'Welcome to Future Now! Find learning, projects and other opportunities.'),
    ('password', 'Пароль для сайту', 'Website password'),
    ('site_login', 'Логін для сайту', 'Website login'),
    ('login_existing', 'Уже є акаунт — увійти', 'Already registered — sign in'),
    ('password_entry_prompt', 'Створіть пароль для входу на сайт: 12–128 символів. Не використовуйте пароль від Telegram чи інших сервісів. Надішліть його повідомленням; бот спробує видалити це повідомлення.', 'Create a website password of 12–128 characters. Do not reuse your Telegram or other passwords. Send it as a message; the bot will try to delete that message.'),
    ('password_confirm_prompt', 'Повторіть новий пароль. Він відкриватиме на сайті цей самий профіль, фільтри й обране.', 'Repeat the new password. It will open the same profile, filters and favorites on the website.'),
    ('password_length', 'Пароль має містити 12–128 символів.', 'Use a password of 12–128 characters.'),
    ('password_mismatch', 'Паролі не збігаються. Повторіть пароль або скасуйте дію.', 'Passwords do not match. Repeat the password or cancel.'),
    ('password_saved', 'Пароль збережено. Входьте на сайт за цим ніком і паролем. Попередні сесії сайту завершено.', 'Password saved. Use this nickname and password on the website. Previous website sessions have been signed out.'),
    ('login_nickname_prompt', 'Введіть нік вашого акаунта Future Now.', 'Enter your Future Now nickname.'),
    ('login_password_prompt', 'Введіть пароль Future Now. Бот спробує видалити повідомлення з паролем.', 'Enter your Future Now password. The bot will try to delete the password message.'),
    ('invalid_credentials', 'Неправильний логін або пароль.', 'Incorrect login or password.'),
    ('login_success', 'Вхід виконано. Профіль, фільтри й обране синхронізовано із сайтом.', 'Signed in. Profile, filters and favorites are shared with the website.'),
    ('telegram_already_linked', 'Цей акаунт уже привʼязаний до іншого Telegram або тут уже є інший логін. Для сайту використайте логін поточного профілю.', 'This account is already linked to another Telegram or this Telegram already has a different login. Use the current profile login on the website.'),
    ('account_busy', 'Інша дія ще виконується. Спробуйте знову.', 'Another action is running. Try again.'),
    ('profile_required', 'Спочатку заповніть профіль.', 'Complete your profile first.'),
    ('too_many_attempts', 'Забагато спроб. Спробуйте через 15 хвилин.', 'Too many attempts. Try again in 15 minutes.'),
    ('invalid_request', 'Перевірте введені дані.', 'Check the submitted fields.'),
    ('nickname_taken', 'Цей нік уже зайнятий. Якщо це ваш акаунт сайту, скористайтеся /login.', 'This nickname is taken. For your existing website account, use /login.')
))
