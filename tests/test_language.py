"""Week two must be consumed, not merely displayed as decorative paperwork."""
import copy
import json
import unittest
from hello_world import pipeline
from hello_world.layers import w20261003 as parliament
from tests.helpers import cli, new_run, remove_run


class LanguageTests(unittest.TestCase):
    def test_language_registered_before_old_stages(self):
        manifest = pipeline.load_manifest()
        self.assertEqual(manifest['weeks'], ['2026-10-03', '2026-10-10', '2026-10-17'])
        self.assertEqual([s['id'] for s in manifest['steps']],
                         ['dictionary', 'translation', 'roundtrip', 'proposal', 'ballot', 'history', 'certificate', 'minutes'])

    def test_roundtrip_is_required_by_parliament(self):
        payload = pipeline.envelope('proposal', None)['payload']
        self.assertIn('language', payload)
        from hello_world.layers import w20261010 as language
        witness = payload['language']
        self.assertEqual(witness['backtranslated'], parliament.proposal())
        self.assertEqual(language.ballot(payload), parliament.ballot(witness['backtranslated']))
        self.assertEqual(len(witness['dictionary']), len(set(parliament.CODEPOINTS)))
        for field in ('dictionary', 'translated', 'backtranslated'):
            missing = copy.deepcopy(payload)
            del missing['language'][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                language.ballot(missing)
            altered = copy.deepcopy(payload)
            altered['language'][field] = []
            with self.subTest(altered=field), self.assertRaises(ValueError):
                language.ballot(altered)
        altered = copy.deepcopy(payload)
        altered['motions'][0]['codepoint'] = 65
        with self.assertRaises(ValueError):
            language.ballot(altered)

    def test_language_tampering_blocks_ballot_and_show(self):
        name, path = new_run()
        path.mkdir(parents=True)
        try:
            for stage in pipeline.STAGES:
                pipeline.run_stage(stage, path)
            source = path / 'proposal.json'
            original = source.read_bytes()
            document = json.loads(original)
            self.assertIn('language', document['payload'])
            for field in ('dictionary', 'translated', 'backtranslated'):
                for changed in (False, True):
                    altered = copy.deepcopy(document)
                    if changed:
                        altered['payload']['language'][field] = []
                    else:
                        del altered['payload']['language'][field]
                    source.write_text(json.dumps(altered))
                    with self.subTest(field=field, changed=changed):
                        result = cli('show', '--run-id', name)
                        self.assertNotEqual(result.returncode, 0)
                        self.assertEqual(result.stdout, b'')
                        with pipeline.ArtifactStore(path) as store:
                            with self.assertRaises(ValueError):
                                pipeline.verified_prefix(store, ('proposal',))
            source.write_bytes(original)
            self.assertEqual(pipeline.display(path), b'HELLO WORLD\n')
        finally:
            remove_run(path)

    def test_old_parliament_still_requires_votes_and_seals(self):
        motions = parliament.proposal()
        votes = parliament.ballot(motions)
        certificates = parliament.certificate(votes)
        minutes = parliament.minutes(certificates)
        self.assertEqual(''.join(e['character'] for e in minutes['entries']), 'HELLO WORLD')
        self.assertEqual(len(votes['ballots']), 11)
        self.assertTrue(all(len(row['votes']) == 5 for row in votes['ballots']))

    def test_tampered_proposal_cannot_enter_ballot(self):
        name, path = new_run()
        path.mkdir(parents=True)
        try:
            pipeline.run_stage('proposal', path)
            source = path / 'proposal.json'
            original = json.loads(source.read_bytes())
            self.assertIn('language', original['payload'])
            for field in ('dictionary', 'translated', 'backtranslated'):
                altered = copy.deepcopy(original)
                del altered['payload']['language'][field]
                source.write_text(json.dumps(altered))
                result = cli('stage', 'ballot', '--run-id', name)
                with self.subTest(field=field):
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stdout, b'')
                    self.assertFalse((path / 'ballot.json').exists())
        finally:
            remove_run(path)
