import hashlib
from urllib.request import urlopen
import client_pf
import client_tf
import time
from datetime import datetime
import random
import logging

logger = logging.getLogger('flask.app')

def sha256sum(img_url):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with urlopen(img_url) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()

def query_mongo(uuid, product, fn, mongo):

    if fn == 2:
        cursor = mongo.db.images.find({"original_image_hash": uuid, "product": product})
        width = cursor[0]['width'] * 4
        height = cursor[0]['height'] * 4
        mockups = cursor[0]['mockups']
        mockups_sorted = sorted(mockups, key=lambda k: k['model'], reverse=True)

        return mockups_sorted, width, height

    elif fn == 3:
        cursor = mongo.db.images.find({"original_image_hash": uuid})
        original_image_url = cursor[0]['original_image_url']

        return original_image_url

def style_image(original_image_url, product, mongo):
    #? Check if ImageHash and Product exists on Mongo
    original_image_hash = sha256sum(original_image_url)
    hashProductDocuments = mongo.db.images.count_documents({"original_image_hash": original_image_hash, "product": product})
    if hashProductDocuments > 0:
        #? If it does exist, just return the mockup urls from Mongo
        print('IMAGE & PRODUCT exists.')
        logger.info('IMAGE & PRODUCT exists.')
    else:
        print('IMAGE & PRODUCT does not exist.')
        logger.info('IMAGE & PRODUCT does not exist.')
        #? If it does not exist, check first if the hash already exists on Mongo (The image could exist for another product)
        hashDocuments = mongo.db.images.count_documents({"original_image_hash": original_image_hash})
        if hashDocuments > 0:
            #? If it does exist, get the styled image url from Mongo 
            logger.info('IMAGE exists. Not calling Tensorflow')
            documents = mongo.db.images.find({"original_image_hash": original_image_hash})
            styled_image_url = documents[0]['styled_image_url']
            width = documents[0]['width']
            height = documents[0]['height']
        else:
            #? If it does not exist, call TF
            logger.info('IMAGE does not exists. Calling Tensorflow')
            img, width, height = client_tf.preprocess_img(original_image_url)
            styled_image_url = client_tf.use_rpc(img, original_image_hash) 

        #? Either case, the mockups do no exist. So, call Printful
        logger.info('Calling Printful.')
        productTaskKey, df = client_pf.post_mockups(width, height, styled_image_url, product)
        logger.info('Sleeping for 11 seconds (Printful requirements)')
        time.sleep(11)
        mockup_urls = client_pf.get_mockups(productTaskKey, product, df)

        #? Write new entry to Mongo
        mongo.db.images.insert({
            "original_image_hash": original_image_hash,
            "product": product,
            "original_image_url": original_image_url,
            "styled_image_url": styled_image_url,
            "width": width,
            "height": height,
            "date": datetime.now(),
            "mockups": mockup_urls
        })

    return original_image_hash
    
