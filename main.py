from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_pymongo import PyMongo

# from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
import logging
import time
import utils

# import sentry_sdk
# from sentry_sdk.integrations.flask import FlaskIntegration

# sentry_sdk.init(
#    "YOUR_URL",
#    integrations=[FlaskIntegration()]
# )

app = Flask(__name__)
app.config["MONGO_URI"] = "YOUR_URL"
mongo = PyMongo(app)
gunicorn_logger = logging.getLogger("gunicorn.error")
app.logger.setLevel(logging.INFO)
app.logger.handlers = gunicorn_logger.handlers


@app.route("/")
def home():
    return render_template("homepage.html")


@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        try:
            uuid = request.form["original_image_hash"]
            original_image_url = utils.query_mongo(uuid, None, 3, mongo)
            return render_template("upload.html", cdn=original_image_url)
        except Exception as e:
            app.logger.error(e)
            # sentry_sdk.capture_exception(e)
            return redirect(url_for("error"))

    return render_template("upload.html")


@app.route("/model", methods=["POST"])
def model():
    try:
        original_image_url = request.form["url"]
        product = request.form["product"]
        app.logger.info("-- CALLING STYLE_IMAGE() --")
        start_time = time.time()
        original_image_hash = utils.style_image(original_image_url, product, mongo)
        end_time = time.time() - start_time
        app.logger.info(
            "-- DONE CALLING STYLE_IMAGE() - {} seconds --".format(end_time)
        )
        redirect_url = f"https://artnie.com/styled/{original_image_hash}/{product}"
        return jsonify({"redirect_url": redirect_url})
    except Exception as e:
        app.logger.error(e)
        # sentry_sdk.capture_exception(e)
        redirect_url = f"https://artnie.com/error"
        return jsonify({"redirect_url": redirect_url})


@app.route("/styled/<uuid>/<product>")
def styled_product(uuid, product):
    try:
        mockups_sorted, width, height = utils.query_mongo(uuid, product, 2, mongo)
        return render_template(
            "styled.html",
            mockups=mockups_sorted,
            original_image_hash=uuid,
            product=product,
            width=width,
            height=height,
        )
    except IndexError:
        return render_template("404.html"), 404
    except Exception as e:
        app.logger.error(e)
        # sentry_sdk.capture_exception(e)
        return redirect(url_for("error"))


@app.route("/error")
def error():
    return render_template("error.html")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(405)
def method_not_allowed(e):
    return render_template("homepage.html"), 405


@app.route("/validate")
def validate():
    return jsonify(
        [
            {"id": 6239, "price": 24, "url": "https://artnie.com/products.json"},
            {"id": 4464, "price": 27, "url": "https://artnie.com/products.json"},
            {"id": 1349, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 3876, "price": 35, "url": "https://artnie.com/products.json"},
            {"id": 6240, "price": 30, "url": "https://artnie.com/products.json"},
            {"id": 4465, "price": 35, "url": "https://artnie.com/products.json"},
            {"id": 3877, "price": 36, "url": "https://artnie.com/products.json"},
            {"id": 6242, "price": 38, "url": "https://artnie.com/products.json"},
            {"id": 1, "price": 39, "url": "https://artnie.com/products.json"},
            {"id": 2, "price": 54, "url": "https://artnie.com/products.json"},
            {"id": 4463, "price": 21, "url": "https://artnie.com/products.json"},
            {"id": 4533, "price": 39, "url": "https://artnie.com/products.json"},
            {"id": 8904, "price": 39, "url": "https://artnie.com/products.json"},
            {"id": 8905, "price": 39, "url": "https://artnie.com/products.json"},
            {"id": 7157, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 7156, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 7911, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 7910, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 8933, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 9621, "price": 33, "url": "https://artnie.com/products.json"},
            {"id": 9620, "price": 33, "url": "https://artnie.com/products.json"},
        ]
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5005)
    # app.run()
