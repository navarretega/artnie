import pandas as pd
import json
import requests
import base64
import time
import logging


class GenericException(Exception):
    """Raise for my specific kind of exception"""


logger = logging.getLogger("flask.app")


def make_req(url, verb, post_json=""):

    api_key = "<YOUR_KEY>"
    api_base64 = base64.b64encode(bytes(api_key, "utf-8"))
    headers = {"Authorization": "Basic {}".format(api_base64.decode("ascii"))}

    if verb == "GET":
        response = requests.get(url, headers=headers)
    else:
        response = requests.post(url, headers=headers, json=post_json)

    if response.status_code == 200:
        results = json.loads(response.content.decode("utf-8"))["result"]
        return results
    else:
        err = response.content
        raise GenericException("Error making request: {}".format(err))


def get_json(variantids, url, width, height):

    # if width > height, show as Landscape / Horizontal
    # if height > width, show as Portrait / Vertical
    # area_width = img_width
    # area_height = img_height

    post_json = {
        "variant_ids": variantids,
        "format": "jpg",
        "files": [
            {
                "placement": "default",
                "image_url": url,
                "position": {
                    "area_width": width,
                    "area_height": height,
                    "width": width,
                    "height": height,
                    "top": 0,
                    "left": 0,
                },
            }
        ],
    }

    return post_json


def post_mockups(width, height, fileurl, product):

    df = pd.read_csv("printful_products.csv", dtype={"VARIANT_ID": str})
    upscaled_width = width * 4
    upscaled_height = height * 4

    df_p = df[df["MODEL"] == product]

    df_p = df_p.assign(isWidthHigherMinDPI=upscaled_width > df_p["MIN_IMG_WIDTH_PX"])
    df_p = df_p.assign(isHeightHigherMinDPI=upscaled_height > df_p["MIN_IMG_HEIGTH_PX"])
    df_p = df_p.assign(
        isWidthandHMeightMinDPI=df_p["isWidthHigherMinDPI"]
        & df_p["isHeightHigherMinDPI"]
    )

    df_p = df_p.assign(isWidthHigherRecDPI=upscaled_width > df_p["REC_IMG_WIDTH_PX"])
    df_p = df_p.assign(isHeightHigherRecDPI=upscaled_height > df_p["REC_IMG_HEIGTH_PX"])
    df_p = df_p.assign(
        isWidthandHMeightRecDPI=df_p["isWidthHigherRecDPI"]
        & df_p["isHeightHigherRecDPI"]
    )

    df_p = df_p.assign(
        MinOrRecDPI=df_p["isWidthandHMeightMinDPI"] | df_p["isWidthandHMeightRecDPI"]
    )

    df_p = df_p.assign(DPI=upscaled_width / df_p["WIDTH_IN"])

    if df_p["MinOrRecDPI"].any():
        # It means there's at least one model with a good resolution

        variantids = df_p["VARIANT_ID"][df_p["MinOrRecDPI"]].tolist()
        prodid = int(df_p["PRODUCT_ID"].unique())

        post_json = get_json(variantids, fileurl, upscaled_width, upscaled_height)
        mockup_generator_url = "https://api.printful.com/mockup-generator/create-task/{}".format(
            prodid
        )
        logger.info("Making POST request to Printful Mockup API")
        res = make_req(mockup_generator_url, "POST", post_json=post_json)

        return res["task_key"], df_p[["VARIANT", "VARIANT_ID", "DPI"]]

    else:
        # Image has bad resolution
        raise GenericException("Image has bad resolution")


def get_mockups(taskKey, product, df):

    logger.info("Making GET request to Printful Mockup API")
    mockup_result_url = "https://api.printful.com/mockup-generator/task?task_key={}".format(
        taskKey
    )

    all_mockup_urls = []

    number_tries = 0
    while True:

        res = make_req(mockup_result_url, "GET")

        if res["status"] == "completed":

            if product in ("ToteBag", "iPhoneCase"):
                mockups = res["mockups"]
                for mockup in mockups:
                    tmp_list = []
                    variantid = mockup["variant_ids"][0]
                    url = mockup["mockup_url"]
                    extras = mockup["extra"]
                    tmp_list.append(url)
                    for extra in extras:
                        url_extra = extra["url"]
                        tmp_list.append(url_extra)

                    variant = df["VARIANT"][df["VARIANT_ID"] == str(variantid)].values[
                        0
                    ]
                    dpi = df["DPI"][df["VARIANT_ID"] == str(variantid)].values[0]

                    if product == "iPhoneCase":
                        price = 33
                    else:
                        price = 39

                        if variant == "Black":
                            copy = tmp_list.copy()
                            for x in copy:
                                if (
                                    x.rsplit("/", 1)[-1] == "9940_default.jpg"
                                    or x.rsplit("/", 1)[-1] == "9943_default.jpg"
                                ):
                                    tmp_list.remove(x)
                        elif variant == "Red":
                            copy = tmp_list.copy()
                            for x in copy:
                                if (
                                    x.rsplit("/", 1)[-1] == "9937_default.jpg"
                                    or x.rsplit("/", 1)[-1] == "9943_default.jpg"
                                ):
                                    tmp_list.remove(x)
                        elif variant == "Yellow":
                            copy = tmp_list.copy()
                            for x in copy:
                                if (
                                    x.rsplit("/", 1)[-1] == "9937_default.jpg"
                                    or x.rsplit("/", 1)[-1] == "9940_default.jpg"
                                ):
                                    tmp_list.remove(x)

                    all_mockup_urls.append(
                        {
                            "model": variant,
                            "mockup_urls": tmp_list,
                            "price": price,
                            "variantid": variantid,
                            "dpi": int(dpi),
                        }
                    )

            elif product in ("Poster"):
                mockups = res["mockups"]
                for mockup in mockups:
                    tmp_list = []
                    variantid = mockup["variant_ids"][0]
                    extras = mockup["extra"]
                    for extra in extras:
                        if extra["title"] == "Person":
                            url_extra = extra["url"]
                            tmp_list.append(url_extra)

                    variant = df["VARIANT"][df["VARIANT_ID"] == str(variantid)].values[
                        0
                    ]
                    dpi = df["DPI"][df["VARIANT_ID"] == str(variantid)].values[0]

                    if variant == "8x10":
                        price = 21
                    elif variant == "10x10":
                        price = 24
                    elif variant == "12x12":
                        price = 27
                    elif variant == "12x16":
                        price = 33
                    elif variant == "12x18":
                        price = 35
                    elif variant == "14x14":
                        price = 30
                    elif variant == "16x16":
                        price = 35
                    elif variant == "16x20":
                        price = 36
                    elif variant == "18x18":
                        price = 38
                    elif variant == "18x24":
                        price = 39
                    elif variant == "24x36":
                        price = 54

                    all_mockup_urls.append(
                        {
                            "model": variant,
                            "mockup_urls": tmp_list,
                            "price": price,
                            "variantid": variantid,
                            "dpi": int(dpi),
                        }
                    )

            logger.info("GET request has completed")
            return all_mockup_urls

        else:
            number_tries += 1
            logger.info("GET request has not completed - Trying again in 3 seconds.")
            time.sleep(3)

            if number_tries > 5:
                raise GenericException("Number of tries limit reached.")

