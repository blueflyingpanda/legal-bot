import telebot
from os import environ
from telebot import types
from docxtpl import DocxTemplate


bot = telebot.TeleBot(environ["TG_TOKEN"])
user_data = {}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.from_user.id, "Добро пожаловать! Нажмите /help чтобы начать.")


@bot.message_handler(commands=['help'])
def send_help(message):
    bot.send_message(
        message.from_user.id,
        "Перед Вами чат бот, который поможет составить договор в сфере медиа.\n"
        "Нажмите /select и выберите интересующий Вас договор. Укажите всю нужную информацию.\n"
        "Получите заполненный вариант договора в формате pdf/docx.\n\n"
        "❗Нажимая /select вы соглашаетесь на обработку персональных данных для заполнения договора.❗\n"
        "Бот не хранит ваши данные после того, как заполняет договор."
    )


@bot.message_handler(commands=['select'])
def send_selection(message):
    keyboard = types.InlineKeyboardMarkup()
    button_contract = types.InlineKeyboardButton(text="Обработка ПД", callback_data="pd")
    button_cancel = types.InlineKeyboardButton(text="Отмена", callback_data="cancel")
    keyboard.add(button_contract, button_cancel)

    bot.send_message(message.from_user.id, "Выберите договор:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    bot.edit_message_reply_markup(
        chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None
    )
    if call.data == "pd":
        bot.answer_callback_query(call.id, "Вы выбрали договор обработки персональных данных.")
        bot.send_message(call.message.chat.id, 'Введите ФИО')
        bot.register_next_step_handler(call.message, get_name)
    elif call.data == "cancel":
        bot.answer_callback_query(call.id, "Вы отменили выбор.")


def get_name(message):
    user_data[message.chat.id] = {}
    user_data[message.chat.id]['name'] = message.text.strip()
    bot.send_message(message.chat.id, 'Введите серию паспорта')
    bot.register_next_step_handler(message, get_pseries)


def get_pseries(message):
    user_data[message.chat.id]['pseries'] = message.text.strip()
    bot.send_message(message.chat.id, 'Введите номер паспорта')
    bot.register_next_step_handler(message, get_pnumber)


def get_pnumber(message):
    user_data[message.chat.id]['pnumber'] = message.text.strip()
    bot.send_message(message.chat.id, 'Введите регистрацию')
    bot.register_next_step_handler(message, get_registration)


def get_registration(message):
    user_data[message.chat.id]['registration'] = message.text.strip()
    bot.send_message(message.chat.id, 'Введите компанию')
    bot.register_next_step_handler(message, get_company)


def get_company(message):
    user_data[message.chat.id]['company'] = message.text.strip()
    bot.send_message(message.chat.id, 'Введите дату в формате чч.мм.гггг')
    bot.register_next_step_handler(message, get_date)


def get_date(message):
    user_data[message.chat.id]['date'] = message.text.strip()
    bot.send_message(message.chat.id, f'Ваш контракт')
    template = DocxTemplate('templates/pd.docx')
    template.render(user_data[message.chat.id])
    template.save('contract.docx')
    with open('contract.docx', 'rb') as fr:
        bot.send_document(message.chat.id, fr)
    del user_data[message.chat.id]
