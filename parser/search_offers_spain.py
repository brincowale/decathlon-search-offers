#!/usr/bin/env python2
#  coding: utf-8
import logging
import re
from pymongo import MongoClient
from grab.spider import Spider, Task
from forocoches_api import ForocochesAPI
from login_config import login as login_fc
import sys


class Decathlon(Spider):

    def prepare(self):
        self.client = MongoClient('mongodb://usuario:password@Server_IP')
        self.db = self.client.decathlon
        self.products_visited = set()
        self.regex_digits = re.compile('\d+')
        self.forocoches = ForocochesAPI(login_fc['username'], login_fc['password'])
        self.base_url = 'http://www.decathlon.'
        # self.regex_digits_decimal = re.compile('\d+,\d+')
        #self.initial_urls = [list(self.db.urls_catalogs.find())][0]
        self.initial_urls = ['http://www.decathlon.es/C-1020908-60']

    def task_initial(self, grab, task):
        for product in grab.doc.select("//li[starts-with(@id,'product_')]"):
            try:
                percentage = product.select('.//span[@class="oldPrice-percentage"]').text()
                percentage = int(self.regex_digits.findall(percentage)[0])
                price = float(product.select('.').attr('data-product-price'))
                # If price and percentage are desired
                if (percentage >= 60 and price <= 2) or (percentage >= 60 and 2 <= price <= 210):
                    # domain = grab.response.url.split('.decathlon.')[1].split('/')[0]
                    product = product.select(".//a[@class='product_name']").attr('href')
                    product_id = int(self.regex_digits.findall(product.split('-id_')[1])[0])
                    if product_id not in self.products_visited:
                        self.products_visited.add(product_id)
                        # When bargain's found, look for it in all countries
                        for country in ['es']:
                            # Check if URL posted previously
                            # if self.db.offers.find({"url": url}).count() == 0:
                            # if self.db.offers.find({"url": {"$regex": "-id_" + str(product_id) + ".html"}}).count() == 0:
                            if self.db.offers.find({"url": {"$regex": "-id_" + str(product_id) + ".html"}}).count() == 0:
                                url = self.base_url + country + product
                                yield Task('extract_data', url=url)

            except Exception as e:
                logging.debug(e)

    def task_extract_data(self, grab, task):
        try:
            # Extract data of product
            title = grab.doc.select('//span[@id="productName"]').text()
            percentage = int(grab.doc.select('//span[@id="promo_percentValue"]').text())
            old_price = grab.doc.select('//span[@id="old_price"]').text()
            old_price = self.regex_digits.findall(old_price)
            old_price = float(old_price[0] + '.' + old_price[1])
            price = float(grab.doc.select('//p[@id="real_price"]').attr('content'))
            try:
                domain = grab.response.url.split('.decathlon.')[1].split('/')[0]
                image = self.base_url + domain + grab.doc.select('.//img[@id="productMainPicture"]/@src').text()
                image = image.replace('/big_', '/classic_')
            except:
                image = "Sin imagen, verificar el producto en otros países"
            if (percentage >= 60 and price <= 2) or (percentage >= 60 and 2 <= price <= 30):
                self.db.offers.insert({"title": title, "old_price": old_price, "image": image, "price": price, "url": grab.response.url, "new": True, "published_telegram": False})
        except Exception as e:
            logging.debug(e)

    def send_mail(self, cursor):
        try:
            msg = ""
            for document in cursor:
                msg += "\n" +\
                    document.get('title').encode('utf-8') + "\nAntes: " +\
                    str(document.get('old_price')) + "€\tAhora: " +\
                    str(document.get('price')) + "€\n" +\
                    document.get('url').encode('utf-8') + "\n\n"
            self.mail.send_mail("Chollos decathlon", msg)
        except Exception as e:
            print(e)

    def publish_forocoches(self, cursor, url):
        msg = ""
        for document in cursor:
            msg += "\n[B][SIZE=3][COLOR=Blue]" +\
                   document.get('title') + "\n[/COLOR][/SIZE][/B]Antes: " +\
                   str(document.get('old_price')) + "EUR\tAhora: [SIZE=3][COLOR=Red][B]" +\
                   str(document.get('price')) + "EUR[/B][/COLOR][/SIZE]\n[IMG]" +\
                   document.get('image') + "[/IMG]\n[PHP]" +\
                   document.get('url') + "[/PHP]\n\n"
        self.forocoches.publish_message_automatically(url, msg) 

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    bot = Decathlon(thread_number=20, network_try_limit=20, task_try_limit=20)
    bot.run()
    cursor = bot.db.offers.find({"url": {"$regex": ".es/"}, "new": True})
    if cursor.count() > 0:
        #bot.send_mail(cursor)
        # 123456 --> ID del hilo de Forocoches
        bot.publish_forocoches(bot.db.offers.find({"url": {"$regex": ".es/"}, "new": True}), '123456')

    bot.db.offers.update({"new": True}, {"$set": {"new": False}}, upsert=False, multi=True)
