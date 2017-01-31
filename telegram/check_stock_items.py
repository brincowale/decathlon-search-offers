# coding: utf-8
import logging
from pymongo import MongoClient
from grab.spider import Spider, Task
from grab import DataNotFound
import decathlon_config as config


class Decathlon(Spider):

    def prepare(self):
        self.client = MongoClient(config.mongodb['uri'])
        self.db = self.client.decathlon
        # Return an url list with following items
        urls = [url['url'] for url in list(self.db.items.find({"search_on": True}, {"url": 1, "_id": 0}))]
        self.initial_urls = list(set(urls))

    def task_initial(self, grab, task):
        try:
            # check if item is in stock, otherwise error DataNotFound will raise
            grab.doc.select('//link[@itemprop="availability"][@href="http://schema.org/InStock"]').attr("href")
            # check if item has stock and has any discount
            if float(grab.doc.select('//span[@id="promo_percentValue"]').text()):
                self.db.items.update({"url": grab.response.url},
                                     {"$set": {"search_on": False, "notify_user": True}}, upsert=False, multi=True)
        except DataNotFound:
            logging.info('Item out of stock')
        except Exception, e:
            logging.error(e)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    bot = Decathlon(thread_number=10, network_try_limit=10, task_try_limit=10)
    bot.run()
