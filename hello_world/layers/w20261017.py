"""Week three: an independent history office must clear all enactments."""
from hello_world.history_verifier import audit
from hello_world.layers import w20261003 as parliament
from hello_world.layers import w20261010 as language
from hello_world.storage import canonical

WEEK = '2026-10-17'


def certificate(previous):
    # The pipeline has already checked the stored proposal and ballot from the
    # start. Recreate its deterministic proposal; audit consumes the actual ballot.
    proposal = language.proposal()
    receipt = audit(proposal, previous)
    return parliament.certificate(previous) | {'history': {
        'proposal': proposal, 'ballot': previous, 'receipt': receipt}}


def minutes(previous):
    try:
        witness = previous['history']
        receipt = audit(witness['proposal'], witness['ballot'])
        if set(witness) != {'proposal', 'ballot', 'receipt'} or canonical(witness['receipt']) != canonical(receipt):
            raise ValueError('missing or altered history receipt')
        certified = parliament.certificate(witness['ballot'])
        if set(previous) != {'certificates', 'history'} or canonical(previous['certificates']) != canonical(certified['certificates']):
            raise ValueError('certificates do not match audited history')
    except (KeyError, TypeError) as error:
        raise ValueError('incomplete history witness') from error
    return parliament.minutes(certified)
