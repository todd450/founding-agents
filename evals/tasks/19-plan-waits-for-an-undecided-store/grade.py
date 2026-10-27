import json
import re


def grade(t):
    yield "opens no build issues", t.output["issues"] == [] and not t.posted("issue create")
    yield "asks about storing addresses or sending mail", t.output["decisions"] and re.search(
        r"stor|database|list|provider|service|mail|send|subscri", json.dumps(t.output["decisions"]), re.I)
    yield "changed no code", not t.moved()
