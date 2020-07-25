from pymongo import MongoClient
import os
from urllib.request import urlretrieve

base = '/home/alex/mockups'

client = MongoClient()
db = client.style_transfer_db
collection = db.styled
documents_not_saved = collection.find({"mockups_saved": 'N'})
for doc in documents_not_saved:
    image_hash = doc['image_hash']
    product = doc['product']
    
    image_path = os.path.join(base, image_hash)
    try:
        os.mkdir(image_path)
    except FileExistsError:
        pass

    product_path = os.path.join(image_path, product)
    try:
        os.mkdir(product_path)
    except FileExistsError:
        pass

    mockups = doc['mockups']
    for mockup in mockups:
        model = mockup['model'].replace(' ', '').replace('/', '-')
        model_path = os.path.join(product_path, model)
        try:
            os.mkdir(model_path)
        except FileExistsError:
            pass
        for mockup_url in mockup['mockup_urls']:
            filename = mockup_url.rsplit('/', 1)[-1]

            urlretrieve(mockup_url, os.path.join(model_path, filename))
            print('Done saving {}'.format(filename))

    
    collection.update_one({'_id': doc['_id']}, {'$set': {'mockups_saved': 'Y'}})

