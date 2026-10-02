"""Week one: a parliament must enact every one of eleven characters."""
import hashlib
from hello_world.storage import canonical

WEEK = "2026-10-03"
SEED = 20261003
CODEPOINTS = (72, 69, 76, 76, 79, 32, 87, 79, 82, 76, 68)
ELECTORS = ("position", "ascii", "agenda", "length", "printability")

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def proposal():
    return {"motions": [{"position": i, "codepoint": code, "motion_id": "M%02d" % i}
                        for i, code in enumerate(CODEPOINTS)]}

def ballot(previous):
    records = []
    for motion in previous["motions"]:
        i, code = motion["position"], motion["codepoint"]
        checks = {"position": 0 <= i < 11, "ascii": 0 <= code < 128,
                  "agenda": code == CODEPOINTS[i], "length": len(previous["motions"]) == 11,
                  "printability": 32 <= code <= 126}
        order = sorted(ELECTORS, key=lambda elector: digest([SEED, i, elector]))
        records.append({"motion": motion, "votes": [{"elector": e, "yes": checks[e]} for e in order]})
    return {"quorum": 5, "majority": 3, "ballots": records}

def certificate(previous):
    certificates = []
    if previous["quorum"] != 5 or previous["majority"] != 3:
        raise ValueError("invalid parliamentary rules")
    for row in previous["ballots"]:
        if {vote["elector"] for vote in row["votes"]} != set(ELECTORS) or len(row["votes"]) != 5:
            raise ValueError("missing or duplicate elector")
        yes = sum(vote["yes"] is True for vote in row["votes"])
        if yes < previous["majority"]:
            raise ValueError("motion rejected")
        body = {"motion": row["motion"], "yes": yes, "ballot_sha256": digest(row)}
        certificates.append(body | {"seal": digest(body)})
    return {"certificates": certificates}

def minutes(previous):
    entries = []
    for row in previous["certificates"]:
        body = {key: value for key, value in row.items() if key != "seal"}
        if row["seal"] != digest(body):
            raise ValueError("invalid enactment seal")
        entries.append({"position": row["motion"]["position"],
                        "character": chr(row["motion"]["codepoint"]),
                        "certificate_seal": row["seal"]})
    entries.sort(key=lambda row: row["position"])
    if [entry["position"] for entry in entries] != list(range(11)):
        raise ValueError("minutes have missing or duplicate positions")
    return {"entries": entries}

BUILDERS = {"proposal": lambda _: proposal(), "ballot": ballot,
            "certificate": certificate, "minutes": minutes}
