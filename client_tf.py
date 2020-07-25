import numpy as np
from tensorflow.contrib.util import make_tensor_proto
from tensorflow_serving.apis import predict_pb2
from tensorflow_serving.apis import prediction_service_pb2_grpc
import grpc

# from skimage.io import imread, imshow
import requests
from PIL import Image, ExifTags
from io import BytesIO
import pyuploadcare
import time
import logging


class GenericException(Exception):
    """Raise for my specific kind of exception"""


logger = logging.getLogger("flask.app")


def humanbytes(B):
    B = float(B)
    KB = float(1024)
    MB = float(KB ** 2)  # 1,048,576
    GB = float(KB ** 3)  # 1,073,741,824
    TB = float(KB ** 4)  # 1,099,511,627,776

    if B < KB:
        return "{0} {1}".format(B, "Bytes" if 0 == B > 1 else "Byte")
    elif KB <= B < MB:
        return "{0:.2f} KB".format(B / KB)
    elif MB <= B < GB:
        return "{0:.2f} MB".format(B / MB)
    elif GB <= B < TB:
        return "{0:.2f} GB".format(B / GB)
    elif TB <= B:
        return "{0:.2f} TB".format(B / TB)


def uploadUploadcare(styled_image_path):

    pyuploadcare.conf.pub_key = "<PUBLIC_KEY>"
    pyuploadcare.conf.secret = "<SECRET_KEY>"

    files = {"file": ("styled.jpg", open(styled_image_path, "rb"), "image/jpeg")}
    fuid = pyuploadcare.api.uploading_request("POST", "base/", files=files)

    number_tries = 0
    while True:

        fileobj = pyuploadcare.api_resources.File(fuid["file"])
        fileurl = fileobj.info()["original_file_url"]

        if fileurl:
            fileobj.store()
            return fileurl
        else:
            number_tries += 1
            time.sleep(1)

            if number_tries > 10:
                raise GenericException("Number of tries limit reached.")


def normalize_arr_of_imgs(arr):

    return arr / 127.5 - 1.0
    # return (arr - np.mean(arr)) / np.std(arr)


def denormalize_arr_of_imgs(arr):

    return (arr + 1.0) * 127.5


def resize_image(img, width=None, height=None):

    (w, h) = img.size

    if width is None:
        r = height / float(h)
        dim = (int(w * r), height)
    else:
        r = width / float(w)
        dim = (width, int(h * r))

    img = img.resize(dim, Image.ANTIALIAS)

    return img


def preprocess_img(url):

    resize_to = 700  # 1280

    response = requests.get(url)
    img = Image.open(BytesIO(response.content))
    img = img.convert("RGB")

    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break
        exif = dict(img._getexif().items())
        if exif[orientation] == 3:
            img = img.rotate(180, expand=True)
        elif exif[orientation] == 6:
            img = img.rotate(270, expand=True)
        elif exif[orientation] == 8:
            img = img.rotate(90, expand=True)
    except (KeyError, AttributeError):
        # cases: image don't have getexif
        pass
    except Exception as e:
        raise GenericException("Could not preprocess image - {}".format(e))

    width, height = img.size

    if width > resize_to and height > resize_to:
        if height > width:
            img_resized = resize_image(img, width=resize_to)
        else:
            img_resized = resize_image(img, height=resize_to)
    else:
        img_resized = img

    r_width, r_height = img_resized.size
    img_original_array = np.array(img)
    img_array = np.array(img_resized)

    logger.info(
        "Original size: {} - {}".format(
            img_original_array.shape[:2], humanbytes(img_original_array.nbytes)
        )
    )
    logger.info(
        "Resize: {} - {}".format(img_array.shape[:2], humanbytes(img_array.nbytes))
    )

    img_array = np.expand_dims(img_array, axis=0)

    return img_array, r_width, r_height


def predictResponse_into_nparray(response, output_tensor_name):
    dims = response.outputs[output_tensor_name].tensor_shape.dim
    shape = tuple(d.size for d in dims)

    return np.reshape(response.outputs[output_tensor_name].float_val, shape)


def use_rpc(img, img_hash):

    channel = grpc.insecure_channel(
        "34.66.28.223:8500",
        options=[
            ("grpc.max_send_message_length", 31457280),
            ("grpc.max_receive_message_length", 31457280),
        ],
    )
    stub = prediction_service_pb2_grpc.PredictionServiceStub(channel)
    request = predict_pb2.PredictRequest()
    request.model_spec.name = "picasso"
    request.model_spec.signature_name = "predict_images"
    request.inputs["images"].CopyFrom(
        make_tensor_proto(img.astype(np.float32), shape=list(img.shape))
    )
    result_future = stub.Predict(request, 30)

    img = predictResponse_into_nparray(result_future, "scores")
    img = img[0]
    img = denormalize_arr_of_imgs(img)
    img_name = "/styled_images/{}_styled.jpg".format(img_hash)
    pimg = Image.fromarray(img.astype("uint8")).convert("RGB")
    pimg.save(img_name)

    logger.info("Styled size: {} - {}".format(img.shape[:2], humanbytes(img.nbytes)))

    logger.info("Uploading styled image.")
    retries = 0
    max_retries = 3

    while retries < max_retries:
        try:
            fileurl = uploadUploadcare(img_name)
            logger.info("DONE uploading styled image.")
            break
        except pyuploadcare.exceptions.APIConnectionError as e:
            logger.info("ERROR uploading styled image. Retrying...")
            time.sleep(2)
        except Exception as oe:
            raise GenericException("Problem uploading with pyuploadcare.")

    if fileurl:
        return fileurl
    else:
        raise GenericException("Fileurl is not valid")

