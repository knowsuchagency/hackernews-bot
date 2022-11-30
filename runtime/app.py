"""
This module contains code to post notifications on new Python stories on the hackernews front page daily or via an
HTTP call.
"""

import os

import requests
from aws_lambda_powertools import Logger
from chalice import Chalice, Cron
from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from pynamodb.exceptions import DoesNotExist
from pynamodb.models import Model

HOST = os.getenv("HOST", "ntfy.sh")
TOPIC = TABLE = SERVICE = os.getenv("TOPIC", "hackernews_python_stories")

logger = Logger(SERVICE)

app = Chalice(app_name=SERVICE)


class Story(Model):
    class Meta:
        table_name = TABLE
        region = "us-east-2"
        billing_mode = "PAY_PER_REQUEST"

    id = UnicodeAttribute(hash_key=True)
    title = UnicodeAttribute()
    url = UnicodeAttribute()
    points = NumberAttribute()


def get_python_stories():
    resp = requests.get(
        "https://hn.algolia.com/api/v1/search?query=python&tags=story&tags=front_page"
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {
            "title": h["title"],
            "url": h["url"],
            "points": h["points"],
            "id": h["objectID"],
        }
        for h in data["hits"]
    ]


def send_notification(title: str, url: str):
    resp = requests.post(
        f"https://{HOST}/{TOPIC}",
        headers={
            "Title": title,
            "Tags": "snake",
        },
        data=url.encode(),
    )


def scan_and_notify():
    """Search for python stories on the front page, and notify on new ones."""
    if not Story.exists():
        logger.info("creating dynamodb table", extra={"table": Story.Meta.table_name})
        Story.create_table(wait=True)

    python_stories = get_python_stories()
    logger.info("fetched stories", extra={"stories": python_stories})

    notifications = 0

    for story in python_stories:

        title = story["title"]
        url = story["url"]
        id = story["id"]
        points = story["points"]

        try:
            story = Story.get(id)
        except DoesNotExist:
            story = Story(
                id=id,
                title=title,
                url=url,
                points=points,
            )
            story.save()
            send_notification(title=title, url=url)
            notifications += 1
        else:
            story.update(actions=[Story.points.set(points)])

    logger.info("finished", extra={"notifications": notifications})

    return notifications


@app.schedule(
    # Run every day at 10am PST (1800 UTC)
    expression=Cron(
        minutes=0,
        hours=18,
        day_of_month="*",
        month="*",
        day_of_week="?",
        year="*",
    ),
    name="hackernews-python",
    description="check for python stories on hacker news",
)
def periodically_scan_and_notify(event, context):
    scan_and_notify()


@app.route("/", methods=["GET"])
def python_stories():
    return [s.attribute_values for s in Story.scan()]


@app.route("/notify", methods=["GET", "POST", "PUT", "PATCH"])
def notify():
    return {"notifications": scan_and_notify()}
