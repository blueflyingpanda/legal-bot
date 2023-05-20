import telebot
import docx2pdf
from os import environ, unlink

from telebot import types
from docxtpl import DocxTemplate

from validators import is_valid_id_series, is_valid_id_number, is_valid_date, is_name_correct, is_regist_correct, \
    is_company_correct

bot = telebot.TeleBot(environ.get('TG_BOT_TOKEN'))
user_data = {}


# MESSAGE HANDLERS #


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.from_user.id, "Добро пожаловать! Нажмите /help чтобы начать.")


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(
        message.from_user.id,
        "Перед Вами чат бот, который поможет составить договор в сфере медиа.\n"
        "Нажмите /select и выберите интересующий Вас договор. Укажите всю нужную информацию или нажмите "
        "/reset, чтобы сбросить ввод данных.\n"
        "Получите заполненный вариант договора в формате pdf/docx.\n\n"
        "❗Нажимая /select вы соглашаетесь на обработку персональных данных для заполнения договора.❗\n"
        "Бот не хранит ваши данные после того, как заполняет договор."
    )


@bot.message_handler(commands=['select'])
def send_selection(message):
    keyboard = types.InlineKeyboardMarkup()
    button_audio_viz = types.InlineKeyboardButton(
        text='Аудиовизуальный контент', callback_data=f'prod_audio_viz')
    button_music_business = types.InlineKeyboardButton(
        text='Музыкальный бизнес', callback_data=f'prod_music_business')
    button_cancel = types.InlineKeyboardButton(text='Отмена', callback_data='cancel')
    keyboard.add(button_audio_viz, button_music_business, button_cancel)

    bot.send_message(message.from_user.id, 'Выберите сферу продюсирования:', reply_markup=keyboard)


@bot.message_handler(commands=['reset'])
def send_reset(message):
    bot.send_message(message.from_user.id, 'Вы перестали заполнять договор.')
    bot.register_next_step_handler(message, lambda message: None)


# CALLBACK HANDLERS #


@bot.callback_query_handler(func=lambda call: call.data.startswith('prod') or call.data == 'cancel')
def handle_selection_callback_query(call):
    """First keyboard"""

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None
    )
    keyboard = types.InlineKeyboardMarkup()
    button_alienation = types.InlineKeyboardButton(text='Отчуждение прав', callback_data='cont_alienation')
    button_order = types.InlineKeyboardButton(text='Авторский заказ', callback_data='cont_order')
    button_licence = types.InlineKeyboardButton(text='Лицензионное соглашение', callback_data='cont_licence')
    button_dummy = types.InlineKeyboardButton(text='Тест', callback_data='cont_dummy')
    button_cancel = types.InlineKeyboardButton(text='Отмена', callback_data='cancel')

    match call.data:
        case 'prod_audio_viz':
            keyboard.add(button_licence)
        case 'prod_music_business':
            keyboard.add(button_order)
        case _:
            bot.answer_callback_query(call.id, 'Вы отменили выбор:(')
            return

    keyboard.add(button_alienation, button_cancel, button_dummy)

    bot.send_message(call.message.chat.id, 'Выберите договор:', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cont') or call.data == 'cancel')
def handle_contract_callback_query(call):
    """Second keyboard"""

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None
    )

    user_data[call.message.chat.id] = {}

    match call.data:
        case 'cont_alienation':
            user_data[call.message.chat.id]['scenario'] = iter(scenario_alienation)
        case 'cont_order':
            user_data[call.message.chat.id]['scenario'] = iter(scenario_order)
        case 'cont_order':
            user_data[call.message.chat.id]['scenario'] = iter(scenario_licence)
        case 'cont_dummy':
            user_data[call.message.chat.id]['scenario'] = iter(scenario_dummy)
        case _:
            bot.answer_callback_query(call.id, 'Вы отменили выбор:(')
            del user_data[call.message.chat.id]
            return

    try:
        next_handler, msg = next(user_data[call.message.chat.id]['scenario'])
    except StopIteration:
        return

    bot.send_message(call.message.chat.id, msg)
    bot.register_next_step_handler(call.message, next_handler)

    user_data[call.message.chat.id]['document'] = 'templates/' + call.data[5:] + '.docx'


@bot.callback_query_handler(func=lambda call: call.data.startswith('format_'))
def handle_format_file(call):
    """Last keyboard"""

    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None
    )

    format = call.data
    message = call.message

    bot.send_message(message.chat.id, f'Ваш контракт')

    template = DocxTemplate(user_data[message.chat.id]['document'])
    template.render(user_data[message.chat.id])
    template.save(f'tmp/{message.chat.id}.docx')

    if format == 'format_docx':
        with open(f'tmp/{message.chat.id}.docx', 'rb') as fr:
            bot.send_document(message.chat.id, fr)
    else:
        docx2pdf.convert(f'tmp/{message.chat.id}.docx', f'tmp/{message.chat.id}.pdf')
        with open(f'tmp/{message.chat.id}.pdf', 'rb') as fr:
            bot.send_document(message.chat.id, fr)
        unlink(f'tmp/{message.chat.id}.pdf')
    unlink(f'tmp/{message.chat.id}.docx')

    del user_data[message.chat.id]


# DECORATORS #


def handler(function):

    def base_handler(*args):
        try:
            next_handler, msg = next(user_data[args[0].chat.id]['scenario'])
        except StopIteration:
            next_handler = msg = None

        if msg:
            bot.send_message(args[0].chat.id, msg)
        if next_handler:
            bot.register_next_step_handler(args[0], next_handler)
        if not msg and not next_handler:
            keyboard = types.InlineKeyboardMarkup()
            but_format_docx = types.InlineKeyboardButton(text='docx', callback_data='format_docx')
            but_format_pdf = types.InlineKeyboardButton(text='pdf', callback_data='format_pdf')
            keyboard.add(but_format_docx, but_format_pdf)

            bot.send_message(args[0].from_user.id, 'В каком /формате вы хотите получить документ?',
                             reply_markup=keyboard)

    def wrapper(*args):
        validation_error = function(args[0])
        if not validation_error:
            base_handler(args[0])

    return wrapper


# STEP HANDLERS #


@handler
def get_name(message):

    name = message.text.strip()

    if not is_name_correct(name):
        bot.send_message(message.chat.id, 'Некорректно введено ФИО, пожалуйста, попробуйте ещё раз')
        bot.register_next_step_handler(message, get_name)
        return True

    user_data[message.chat.id]['name'] = name


@handler
def get_series(message):
    series = message.text.strip()

    if not is_valid_id_series(series):
        bot.send_message(message.chat.id, 'Некорректно введена серия паспорта, пожалуйста, попробуйте ещё раз')
        bot.register_next_step_handler(message, get_series)
        return True

    user_data[message.chat.id]['series'] = series


@handler
def get_number(message):
    number = message.text.strip()

    if not is_valid_id_number(number):
        bot.send_message(message.chat.id, 'Некорректно введен номер паспорта, пожалуйста, попробуйте ещё раз')
        bot.register_next_step_handler(message, get_number)
        return True

    user_data[message.chat.id]['number'] = number


@handler
def get_registration(message):
    registration = message.text.strip()

    if not is_regist_correct(registration):
        bot.send_message(message.chat.id, 'Некорректно введена регистрация, пожалуйста, попробуйте ещё раз')
        bot.register_next_step_handler(message, get_registration)
        return True

    user_data[message.chat.id]['registration'] = registration


@handler
def get_company(message):
    company = message.text.strip()

    if not is_company_correct(company):
        bot.send_message(message.chat.id, 'Некорректно введена компания, пожалуйста, попробуйте ещё раз')
        bot.register_next_step_handler(message, get_company)
        return True

    user_data[message.chat.id]['company'] = company


@handler
def get_date(message):
    """Always last"""

    date = message.text.strip()

    if not is_valid_date(date):
        bot.send_message(message.chat.id, 'Некорректно введена дата, пожалуйста, попробуйте ещё раз')
        bot.register_next_step_handler(message, get_date)
        return True

    user_data[message.chat.id]['date'] = date


# SCENARIO


scenario_dummy = [
    (get_name, 'Вы выбрали договор чего-то там\nВведите ФИО. Требования к вводу/пример: Паленов Матвей Октавианович'),
    (get_series, 'Введите серию паспорта'),
    (get_number, 'Введите номер паспорта'),
    (get_registration, 'Введите регистрацию'),
    (get_company, 'Введите компанию'),
    (get_date, 'Введите дату в формате чч.мм.гггг'),
]
scenario_alienation = []
scenario_order = []
scenario_licence = []
