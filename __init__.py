from . import PrintunaExtension


def getMetaData():
    return {}


def register(app):
    return {"extension": PrintunaExtension.PrintunaExtension()}
