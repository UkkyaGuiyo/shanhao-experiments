"""Independent finite transcript verifier; never calls the transcript producers.

Hashes attest internal consistency, not identity, origin or a real signature.
"""
import hashlib
from hello_world.layers.w20261003 import CODEPOINTS, ELECTORS, SEED
from hello_world.storage import canonical


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def audit(proposal, ballot):
    # Reconstruct the fixed protocol here, without trusting producer callbacks.
    codes = sorted(set(CODEPOINTS))
    lexicon = [{'word': 's%02d' % i, 'codepoint': code} for i, code in enumerate(codes)]
    motions, translations, votes = [], [], []
    records = []
    head = digest({'protocol': 'history-2026-10-17', 'seed': SEED})
    for position, code in enumerate(CODEPOINTS):
        motion = {'position': position, 'motion_id': 'M%02d' % position, 'codepoint': code}
        translation = {'position': position, 'motion_id': motion['motion_id'],
                       'word': 's%02d' % codes.index(code)}
        order = sorted(ELECTORS, key=lambda elector: digest([SEED, position, elector]))
        vote = {'motion': motion, 'votes': [{'elector': elector, 'yes': True} for elector in order]}
        motions.append(motion)
        translations.append(translation)
        votes.append(vote)
        body = {'position': position, 'previous': head, 'motion_sha256': digest(motion),
                'translation_sha256': digest(translation), 'ballot_sha256': digest(vote)}
        head = digest(body)
        records.append(body | {'seal': head})
    expected_proposal = {'motions': motions, 'language': {
        'dictionary': lexicon, 'translated': translations, 'backtranslated': {'motions': motions}}}
    expected_ballot = {'quorum': 5, 'majority': 3, 'ballots': votes}
    # Canonical bytes also reject bool/int substitution, unknown fields and reordering.
    if canonical(proposal) != canonical(expected_proposal):
        raise ValueError('history translation transcript rejected')
    if canonical(ballot) != canonical(expected_ballot):
        raise ValueError('history voting transcript rejected')
    return {'protocol': 'history-2026-10-17', 'proposal_sha256': digest(proposal),
            'ballot_sha256': digest(ballot), 'records': records, 'votes': 55, 'root': head}
