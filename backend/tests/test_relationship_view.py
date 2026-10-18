import unittest

from backend.relationship_view import build_relationship_view


class RelationshipViewTests(unittest.TestCase):
    def build(self, **values):
        data = dict(snapshot={'case': {'id': 'CASE-A', 'title': 'Test case'},
                              'evidence': [{'id': 'ART-A', 'name': 'sample.wav', 'type': 'Audio'}]},
                    entities=[], relations=[], inspections=[], episodes=[], reports=[], graph_available=True)
        data.update(values)
        return build_relationship_view(**data)

    def test_membership_does_not_claim_cause(self):
        data = self.build()
        self.assertEqual(data['edges'][0]['state'], 'membership')
        self.assertIn('not a causal relationship', data['edges'][0]['reason'])

    def test_missing_endpoints_are_not_fabricated(self):
        data = self.build(relations=[{'from': 'ART-A', 'to': 'FOREIGN', 'label': 'USED', 'state': 'candidate'}])
        self.assertEqual(len(data['edges']), 1)
        self.assertNotIn('FOREIGN', {node['id'] for node in data['nodes']})

    def test_candidate_state_and_source_are_preserved(self):
        data = self.build(entities=[{'id': 'ACC-A', 'name': 'account', 'label': 'Account', 'source': 'ART-A', 'claim': 'candidate'}],
                          relations=[{'from': 'ACC-A', 'to': 'ART-A', 'label': 'USED', 'state': 'candidate', 'source': 'ART-A'}])
        link = next(e for e in data['edges'] if e['label'] == 'used')
        self.assertEqual(link['state'], 'candidate')
        self.assertEqual(link['sources'], ['ART-A'])


if __name__ == '__main__':
    unittest.main()
