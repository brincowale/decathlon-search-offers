#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Simple Bot to reply to Telegram messages
# This program is dedicated to the public domain under the CC0 license.

"""
This Bot uses the Updater class to handle the bot.
First, a few handler functions are defined. Then, those functions are passed to
the Dispatcher and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Basic Echobot example, repeats messages.
Press Ctrl-C on the command line or send a signal to the process to stop the
bot.
"""

from telegram import Updater
import re
import logging
from pymongo import MongoClient
import decathlon_config as config

# Enable logging
logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO)

logger = logging.getLogger(__name__)

# Connect to DB
client = MongoClient(config.mongodb['uri'])
db = client.decathlon

# regex expressions
regex_product_url = re.compile("^https?://www.decathlon.[a-z]{2}(.[a-z]{2})?/[a-zA-Z0-9\-]*-id_[0-9]{4,10}.html$")

# Define a few command handlers. These usually take the two arguments bot and
# update. Error handlers also receive the raised TelegramError object in error.
def start(bot, update):
    bot.sendMessage(update.message.chat_id, text='Escribe /help para ver la ayuda')


def help_info(bot, update):
    param = update.message.text.split(' ')[1].strip()
    if param == 'add':
        msg = "Para añadir un producto a tu lista de seguimiento debes escribir:\n"\
            "/add url_del_producto\n\n"\
            "Ejemplo: /add http://www.decathlon.es/camiseta-termica-manga-larga-hombre-btwin-520-negra-id_8315333.html\n\n"\
            "El enlace no debe contener espacios, referencias de afiliación ni cualquier otro simbolo como ? o #.\n"
    elif param == 'del':
        msg = "Para eliminar un producto de tu lista de seguimiento debes escribir:\n"\
            "/del url_del_producto\n\n"\
            "Ejemplo: /del http://www.decathlon.es/camiseta-termica-manga-larga-hombre-btwin-520-negra-id_8315333.html\n\n"\
            "El enlace no debe contener espacios, referencias de afiliación ni cualquier otro simbolo como ? o #.\n"
    else:
        msg = 'Solicitar permiso: /addme\n'\
                'Añadir producto: /help add\n'\
                'Eliminar producto: /help del\n'\
                'Listar tus productos: /list\n'\
                'Reactivar la búsqueda de todos tus productos: /readd\n'\
                'Ver la URL del canal de chollos: /canal\n'\
                '\nUn ejemplo de URL del producto es esta (sin stock y con descuento): http://www.decathlon.es/cesta-bici-300-del-violeta-id_8328713.html\n'\
                '\n¡Este bot es solo para productos sin stock, no para saber cuando un producto baja de precio!'
    bot.sendMessage(update.message.chat_id, text=msg)


def is_user_authorized(bot, user_id):
    try:
        if [document.get('allowed_user') for document in db.users.find({"user_id": str(user_id)})][0]:
            return True
        else:
            return False
    except Exception, e:
        logging.error(e)
        # TODO when exception error sql not found, send this message
        bot.sendMessage(user_id, text='¡Usuario no autorizado!')


def add_item(bot, update):
    """
    notify_user: is True when an offer has found and need notify the user
    search_on: is true when the user need search that product
    :param bot:
    :param update:
    :return:
    """
    item_url_to_add = update.message.text.split(' ')[1].strip()
    if regex_product_url.match(item_url_to_add):
        if is_user_authorized(bot, update.message.chat.id):
            # add the product in the database if not added previously by the user
            if db.items.find({"user_id": str(update.message.chat.id), "url": item_url_to_add}).count() == 0:
                db.items.insert({"url": item_url_to_add, "notify_user": False, 'search_on': True,
                                    'first_name': update.message.chat.first_name, 'user_id': str(update.message.chat.id)})
                bot.sendMessage(update.message.chat_id, text='Producto en seguimiento')
            else:
                bot.sendMessage(update.message.chat_id, text='¡Enlace añadido previamente!')
    else:
        bot.sendMessage(update.message.chat_id, text='Datos incorrectos, consulta la ayuda con /help add')


def del_item(bot, update):
    item_url_to_add = update.message.text.split(' ')[1].strip()
    if regex_product_url.match(item_url_to_add):
        if is_user_authorized(bot, update.message.chat.id):
            # remove the url from database
            if db.items.find({"user_id": str(update.message.chat.id), "url": item_url_to_add}).count() > 0:
                db.items.remove({"url": item_url_to_add, 'user_id': str(update.message.chat.id)})
                bot.sendMessage(update.message.chat_id, text='Producto eliminado')
            else:
                bot.sendMessage(update.message.chat_id, text='La URL indroducida no existe en tu lista')
    else:
        bot.sendMessage(update.message.chat_id, text='Datos incorrectos, consulta la ayuda con /help del')


def readd_items(bot, update):
    if is_user_authorized(bot, update.message.chat.id):
        db.items.update({"search_on": False, 'notify_user': False, "user_id": str(update.message.chat.id)},
                        {"$set": {"search_on": True, 'notify_user': True}}, upsert=False, multi=True)
        bot.sendMessage(update.message.chat_id, text='Producto reañadidos')


def list_items(bot, update):
    if is_user_authorized(bot, update.message.chat.id):
        msg = 'True: sigues buscando el producto\n' \
          'False: ya no buscas el producto\n\n' \
          'Listado de productos:\n'
        for document in db.items.find({"user_id": str(update.message.chat.id)}):
            msg += str(document.get('search_on')) + ' - ' + document.get('url') + '\n\n'
        bot.sendMessage(update.message.chat_id, text=msg)


def canal(bot, update):
    if is_user_authorized(bot, update.message.chat.id):
        bot.sendMessage(update.message.chat_id, text='ES - https://telegram.me/joinchat/xxxxxxxxxxx\n'\
                                                     'DE - https://telegram.me/joinchat/yyyyyyyyyyy')


def add_user(bot, update):
    if db.users.find({"user_id": str(update.message.chat.id)}).count() == 0:
        bot.sendMessage(update.message.chat_id, text='Añadido correctamente, la verificación se realizará manualmente')
        db.users.insert({"user_id": str(update.message.chat.id), "first_name": update.message.chat.first_name,
                         "username": update.message.chat.username, 'allowed_user': False})
    else:
        bot.sendMessage(update.message.chat_id, text='Ya estas en la lista de espera')


def echo(bot, update):
    bot.sendMessage(update.message.chat_id, text=update.message.text)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def track_items(bot):
    for document in db.items.find({"notify_user": True}):
        bot.sendMessage(document.get('user_id'), text='Re-Stock\n' + document.get('url'))
        db.items.update({"user_id": document.get('user_id'), "url": document.get('url'),
                         'notify_user': True}, {"$set": {"notify_user": False}}, upsert=False, multi=True)


def publish_new_offers(bot):
    for document in db.offers.find({"published_telegram": False, "url": {"$regex": ".es/"}}):
        bot.sendMessage('-000000000000', text=document.get('url'))
    db.offers.update({"published_telegram": False, "url": {"$regex": ".es/"}}, {"$set": {"published_telegram": True}}, upsert=False, multi=True)

    for document in db.offers.find({"published_telegram": False, "url": {"$regex": ".de/"}}):
        bot.sendMessage('-111111111111', text=document.get('url'))
    db.offers.update({"published_telegram": False, "url": {"$regex": ".de/"}}, {"$set": {"published_telegram": True}}, upsert=False, multi=True)


def main():
    # Create the EventHandler and pass it your bot's token.
    updater = Updater("123456789:ABCDEFGHIJKLM")
    job_queue = updater.job_queue
    job_queue.put(track_items, 60, next_t=0)
    #job_queue.put(publish_new_offers, 60, next_t=0)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.addTelegramCommandHandler("start", start)
    dp.addTelegramCommandHandler("help", help_info)
    dp.addTelegramCommandHandler("add", add_item)
    dp.addTelegramCommandHandler("list", list_items)
    dp.addTelegramCommandHandler("readd", readd_items)
    dp.addTelegramCommandHandler("addme", add_user)
    dp.addTelegramCommandHandler("del", del_item)
    dp.addTelegramCommandHandler("canal", canal)

    # on noncommand i.e message - echo the message on Telegram
    dp.addTelegramMessageHandler(echo)

    # log all errors
    dp.addErrorHandler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until the you presses Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
