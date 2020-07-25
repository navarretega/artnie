import client_tf
import hashlib
from urllib.request import urlopen

def sha256sum(img_url):
    h  = hashlib.sha256()
    b  = bytearray(128*1024)
    mv = memoryview(b)
    with urlopen(img_url) as f:
        for n in iter(lambda : f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


original_image_url = 'https://ucarecdn.com/6a83b29a-f882-4b25-85d4-77f65299fbbc/Alejandro_21.jpg'
original_image_hash = sha256sum(original_image_url)
img, width, height = client_tf.preprocess_img(original_image_url)
styled_image_url = client_tf.use_rpc(img, original_image_hash)
