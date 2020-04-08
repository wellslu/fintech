import requests
import configparser
import telegram
from flask import Flask, request
from telegram.ext import Dispatcher, MessageHandler, Filters, Updater, CommandHandler, InlineQueryHandler, CommandHandler
from fugle_realtime import intraday
from datetime import datetime,timedelta
import pandas as pd
import sys
import matplotlib.pyplot as plt
import time
config = configparser.ConfigParser()
config.read('config.ini')
access_token = config['TELEGRAM']['ACCESS_TOKEN']
webhook_url = config['TELEGRAM']['WEBHOOK_URL']
requests.post('https://api.telegram.org/bot'+access_token+'/deleteWebhook').text
requests.post('https://api.telegram.org/bot'+access_token+'/setWebhook?url='+webhook_url+'/hook').text
df = pd.read_csv(r'C:\Users\wells\0319_ntu_scu\fugle_telegram_chatbot\symbol_info.csv',encoding='utf8')

# Initial Flask app
app = Flask(__name__)

# Initial bot by Telegram access token
bot = telegram.Bot(token=config['TELEGRAM']['ACCESS_TOKEN'])
stock = None
api = '51714d20eae11ba0c9c9647cab45da4b'

s=0
@app.route('/hook', methods=['POST'])
def webhook_handler():
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        # Update dispatcher process that handler to process this message
        dispatcher.process_update(update)
    return 'ok'

## reply message
def reply_handler(bot, update):
    global s
    global api
    global stock
    global df
    text = update.message.text
    if text == '/start':
        update.message.reply_text('do u want /search stock symbolId or check stock /data?')
        s = 1
    elif 'restart' in text and s == 1:
        stock = None
        update.message.reply_text('do u want /search stock symbolId or check stock /data?')
    elif s == 0:
        update.message.reply_text('please enter \'/start\' to start fintech')
    else:
        if stock is None:
            if 'search' in text:
                s = 2
                update.message.reply_text('enter the company name')
            elif s == 2:
                df1 = df[df['name'].isin([text])].reset_index(drop = True)
                try:
                    name = df1['symbol_id'][0]
                    update.message.reply_text(name)
                    s = 1
                except:
                    update.message.reply_text('no this company')
                    s = 1
            elif 'data' in text:
                s = 3
                update.message.reply_text('enter the company symbolId')
            elif s == 3:
                meta = intraday.meta(apiToken=api,symbolId=text,output='raw')
                try:
                    e = meta['error']['message']
                    update.message.reply_text(meta['error']['message'])
                    s = 1
                except:
                    stock = text
                    update.message.reply_text('What do u want to search with ' + meta['nameZhTw']+'\nu can enter:\n/priceReference\n/priceOpen\n/priceNow\n/bestBidsandAsks\n/graph\n/restart')
                    s = 1
            else:
                update.message.reply_text('I don\'t know what u want')
        elif 'priceReference' in text:
            meta = intraday.meta(apiToken=api,symbolId=stock,output='raw')
            priceReference = str(meta['priceReference'])
            priceHighLimit = str(meta['priceHighLimit'])
            priceLowLimit = str(meta['priceLowLimit'])
            update.message.reply_text('Today priceReference\npriceReference: {}\npriceHighLimit: {}\npriceLowLimit: {}'.format(priceReference,priceHighLimit,priceLowLimit))
        elif 'priceOpen' in text:
            quote = intraday.quote(apiToken=api,symbolId=stock,output='raw')
            priceOpen = str(quote['priceOpen']['price'])
            priceHigh = str(quote['priceHigh']['price'])
            priceLow = str(quote['priceLow']['price'])
            update.message.reply_text('Today priceOpen\npriceOpen: {}\npriceHigh: {}\npriceLow: {}'.format(priceOpen,priceHigh,priceLow))
        elif 'priceNow' in text:
            quote = intraday.quote(apiToken=api,symbolId=stock,output='raw')
            price = str(quote['trade']['price'])
            unit = str(quote['trade']['unit'])
            at = quote['trade']['at']
            at = str(datetime.strptime(at[0:-5],"%Y-%m-%dT%H:%M:%S")+timedelta(hours=8))
            update.message.reply_text('Newest trade\ntrade price: {}\ntrade unit: {}\ntrade time: {}'.format(price,unit,at))
        elif 'bestBidsandAsks' in text:
            quote = intraday.quote(apiToken=api,symbolId=stock,output='raw')
            at = quote['order']['at']
            at = str(datetime.strptime(at[0:-5],"%Y-%m-%dT%H:%M:%S")+timedelta(hours=8))
            bestBids = quote['order']['bestBids']
            bestAsks = quote['order']['bestAsks']
            BidsUnit = [n['unit'] for n in bestBids]
            BidsUnit.reverse()
            BidsPrice = [n['price'] for n in bestBids]
            BidsPrice.reverse()
            AsksPrice = [n['price'] for n in bestAsks]
            AsksUnit = [n['unit'] for n in bestAsks]
            df = pd.DataFrame({'BidsUnit':BidsUnit,'BidsPrice':BidsPrice,'AsksPrice':AsksPrice,'AsksUnit':AsksUnit})
            update.message.reply_text(df.to_string(index=False)+'\ntime: {}'.format(at))
        elif 'graph' in text:
            data = intraday.chart(apiToken=api,symbolId=stock)
            data['time'] = data['at'] - data['at'][0]
            data['date'] = data['at'] - data['at'][0] + timedelta(hours=9) + timedelta(minutes=1)
            # data['date'] = data['date'].strftime('%H:%M')
            def abc(aa):
                aa['time'] = aa['time'].seconds/60+1
                aa['time'] = int(aa['time'])
                aa['date'] = str(aa['date']).split(' ')[2]
                return aa
            data = data.apply(abc,axis=1)
            meta = intraday.meta(apiToken=api,symbolId=stock,output='raw')
            priceLowLimit = meta['priceLowLimit']
            priceHighLimit = meta['priceHighLimit']
            priceReference = meta['priceReference']
            x = list(data['time'])
            y = data['close']
            plt.figure()
            plt.plot(x, y, color='b', linewidth=1.0)
            plt.xticks([0,60,120,180,240,270],['09:00','10:00','11:00','12:00','13:00','13:30'])
            plt.yticks([priceLowLimit,(priceLowLimit+priceReference)/2,priceReference,(priceReference+priceHighLimit)/2,priceHighLimit])
            ax = plt.gca()
            ax.spines['right'].set_color('none')
            ax.spines['top'].set_color('none')
            plt.xlim((0,270))
            plt.ylim((priceLowLimit, priceHighLimit))
            plt.xlabel(r'$time$')
            plt.ylabel(r'$price$')
            y0 = priceReference
            plt.plot([0,270] ,[y0,y0],'k-',lw=0.5)
            plt.fill_between(x,y,y0,where= y<=y0,facecolor='g',interpolate= True,alpha=0.3)
            plt.fill_between(x,y,y0,where= y>=y0,facecolor='r',interpolate= True,alpha=0.3)
            plt.title(stock)
            plt.savefig('graph.png')
            chat_id = update.message.chat_id
            bot.send_photo(chat_id=chat_id, photo=open('graph.png', 'rb'))
        else:
            update.message.reply_text('I don\'t know what u want')
            
# This class dispatches all kinds of updates to its registered handlers.
dispatcher = Dispatcher(bot, None)
dispatcher.add_handler(MessageHandler(Filters.text, reply_handler))

if __name__ == '__main__':
    app.run()
