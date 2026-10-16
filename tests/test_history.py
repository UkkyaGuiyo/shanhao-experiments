"""Week three: independent historical audit is mandatory for minutes."""
import copy
import json
import unittest
from hello_world import pipeline
from tests.helpers import new_run, remove_run


class HistoryTests(unittest.TestCase):
    def certificate(self):
        previous = None
        for stage in ('proposal', 'ballot', 'certificate'):
            previous = pipeline.envelope(stage, previous)
        return previous['payload']

    def test_history_is_required_by_minutes(self):
        document = self.certificate()
        self.assertIn('history', document)
        from hello_world.layers import w20261017 as history
        self.assertEqual(history.minutes(document)['entries'][0]['character'], 'H')
        for field in ('proposal', 'ballot', 'receipt'):
            changed = copy.deepcopy(document)
            del changed['history'][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                history.minutes(changed)

    def test_independent_verifier_rejects_forged_history(self):
        document = self.certificate()
        self.assertIn('history', document)
        from hello_world.layers import w20261017 as history
        for mutate in (
            lambda h: h['proposal']['language']['dictionary'].reverse(),
            lambda h: h['proposal']['language']['translated'][0].update(word='s00'),
            lambda h: h['proposal']['language']['backtranslated']['motions'].reverse(),
            lambda h: h['ballot']['ballots'][0]['votes'][0].update(yes=False),
            lambda h: h['ballot']['ballots'].reverse(),
            lambda h: h['receipt'].update(root='0' * 64),
        ):
            changed = copy.deepcopy(document)
            mutate(changed['history'])
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                history.minutes(changed)

    def test_history_receipt_is_deterministic_and_complete(self):
        document = self.certificate()
        self.assertIn('history', document)
        from hello_world.layers import w20261017 as history
        witness = document['history']
        self.assertEqual(history.audit(witness['proposal'], witness['ballot']), witness['receipt'])
        self.assertEqual(len(witness['receipt']['records']), 11)
        self.assertEqual(witness['receipt']['votes'], 55)
        self.assertEqual(document, self.certificate())

    def test_history_absence_or_change_blocks_final_output(self):
        _, path = new_run()
        path.mkdir(parents=True)
        try:
            for stage in pipeline.STAGES:
                pipeline.run_stage(stage, path)
            source = path / 'certificate.json'
            original = json.loads(source.read_bytes())
            self.assertIn('history', original['payload'])
            for changed in (False, True):
                altered = copy.deepcopy(original)
                if changed:
                    altered['payload']['history']['receipt']['root'] = '0' * 64
                else:
                    del altered['payload']['history']
                source.write_text(json.dumps(altered))
                with self.subTest(changed=changed), self.assertRaises(ValueError):
                    pipeline.display(path)
        finally:
            remove_run(path)

    def test_old_certificates_cannot_bypass_history(self):
        document = self.certificate()
        self.assertIn('history', document)
        from hello_world.layers import w20261017 as history
        del document['history']
        with self.assertRaises(ValueError):
            history.minutes(document)

    def test_verifier_does_not_call_translation_or_ballot_producers(self):
        document = self.certificate()
        self.assertIn('history', document)
        from unittest.mock import patch
        from hello_world.layers import w20261017 as history
        with patch('hello_world.layers.w20261010.proposal', side_effect=AssertionError('producer called')), \
             patch('hello_world.layers.w20261003.ballot', side_effect=AssertionError('producer called')):
            self.assertEqual(len(history.minutes(document)['entries']), 11)

    def test_certificates_must_match_audited_ballots(self):
        document = self.certificate()
        self.assertIn('history', document)
        from hello_world.layers import w20261017 as history
        document['certificates'][0]['yes'] = 4
        with self.assertRaises(ValueError):
            history.minutes(document)
