"""Week four: output consumes the mandatory typesetter's punched cards."""
import copy
import unittest
from hello_world import pipeline

class PunchcardTests(unittest.TestCase):
    def minutes(self):
        previous = None
        for stage in pipeline.STAGES:
            previous = pipeline.envelope(stage, previous)
        return previous['payload']

    def test_cards_are_mandatory(self):
        document = self.minutes()
        self.assertIn('punchcards', document)
        from hello_world.layers import w20261024 as office
        del document['punchcards']
        with self.assertRaises(ValueError):
            office.decode(document)

    def test_card_format_and_output(self):
        document = self.minutes()
        self.assertIn('punchcards', document)
        from hello_world.layers import w20261024 as office
        self.assertEqual(len(document['punchcards']), 11)
        self.assertEqual(office.decode(document), b'HELLO WORLD\n')
        self.assertEqual(document, self.minutes())

    def test_tampering_rejected(self):
        document = self.minutes()
        self.assertIn('punchcards', document)
        from hello_world.layers import w20261024 as office
        for mutate in (
            lambda d: d['punchcards'].pop(),
            lambda d: d['punchcards'].reverse(),
            lambda d: d['punchcards'].__setitem__(1, d['punchcards'][0]),
            lambda d: d['punchcards'][0]['holes'].__setitem__(0, True),
            lambda d: d['punchcards'][0]['holes'].__setitem__(0, 2),
            lambda d: d['punchcards'][0]['holes'].__setitem__(0, 0),
            lambda d: d['punchcards'][0].update(parity=99),
            lambda d: d['punchcards'][0].update(certificate_seal='forged'),
            lambda d: d['punchcards'][0].update(position=99),
            lambda d: d['entries'][0].update(character='X'),
        ):
            changed = copy.deepcopy(document)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                office.decode(changed)

    def test_old_minutes_rejected(self):
        document = self.minutes()
        self.assertIn('punchcards', document)
        from hello_world.layers import w20261024 as office
        with self.assertRaises(ValueError):
            office.decode({'entries': document['entries']})

    def test_preserves_history_validation(self):
        document = None
        for stage in ('proposal', 'ballot', 'certificate'):
            document = pipeline.envelope(stage, document)
        from hello_world.layers import w20261024 as office
        del document['payload']['history']
        with self.assertRaises(ValueError):
            office.minutes(document['payload'])

    def test_display_consumes_decoder(self):
        from unittest.mock import patch
        from tests.helpers import new_run, remove_run
        _, path = new_run()
        path.mkdir(parents=True)
        try:
            for stage in pipeline.STAGES:
                pipeline.run_stage(stage, path)
            with patch('hello_world.pipeline.typesetter.decode', return_value=b'decoder sentinel') as decoder:
                self.assertEqual(pipeline.display(path), b'decoder sentinel')
                decoder.assert_called_once()
        finally:
            remove_run(path)
