"""Week two: motions need a tiny language and a verified return translation."""
from hello_world.layers import w20261003 as parliament

WEEK = "2026-10-10"


def dictionary():
    return [{"word": "s%02d" % i, "codepoint": code}
            for i, code in enumerate(sorted(set(parliament.CODEPOINTS)))]


def translate(motions, lexicon):
    words = {row["codepoint"]: row["word"] for row in lexicon}
    return [{"position": row["position"], "motion_id": row["motion_id"],
             "word": words[row["codepoint"]]} for row in motions]


def backtranslate(translated, lexicon):
    codes = {row["word"]: row["codepoint"] for row in lexicon}
    return {"motions": [{"position": row["position"], "motion_id": row["motion_id"],
                         "codepoint": codes[row["word"]]} for row in translated]}


def proposal():
    original = parliament.proposal()
    lexicon = dictionary()
    translated = translate(original["motions"], lexicon)
    restored = backtranslate(translated, lexicon)
    if restored != original:
        raise ValueError("motion translation did not round-trip")
    return original | {"language": {"dictionary": lexicon, "translated": translated,
                                    "backtranslated": restored}}


def ballot(previous):
    # A complete, deterministic witness is mandatory even for direct callers.
    if previous != proposal():
        raise ValueError("missing or altered motion language witness")
    witness = previous["language"]
    restored = backtranslate(witness["translated"], witness["dictionary"])
    if restored != witness["backtranslated"] or restored["motions"] != previous["motions"]:
        raise ValueError("motion translation did not round-trip")
    # The old parliament votes on the decoded result, never a bypass copy.
    return parliament.ballot(restored)
