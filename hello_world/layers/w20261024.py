"""Week four: minutes must be punched onto cards before they can be read."""
from hello_world.layers import w20261017 as history
from hello_world.storage import canonical

WEEK = '2026-10-24'


def punch(entries):
    if len(entries) != 11:
        raise ValueError('eleven typesetting orders required')
    cards = []
    for position, entry in enumerate(entries):
        code = ord(entry['character'])
        if entry['position'] != position or not 32 <= code <= 126:
            raise ValueError('invalid typesetting order')
        holes = [(code >> shift) & 1 for shift in range(6, -1, -1)]
        cards.append({'position': position, 'holes': holes,
                      'parity': sum(holes) % 2,
                      'certificate_seal': entry['certificate_seal']})
    return cards


def minutes(previous):
    # All old validation and minutes compilation remain prerequisites.
    document = history.minutes(previous)
    return document | {'punchcards': punch(document['entries'])}


def decode(document):
    try:
        if set(document) != {'entries', 'punchcards'}:
            raise ValueError('missing typesetting witness')
        cards = document['punchcards']
        if canonical(cards) != canonical(punch(document['entries'])):
            raise ValueError('altered, missing or reordered punchcard')
        output = bytearray()
        for card in cards:
            code = 0
            for hole in card['holes']:
                code = (code << 1) | hole
            output.append(code)
        return bytes(output) + b'\n'
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError('incomplete typesetting witness') from error
