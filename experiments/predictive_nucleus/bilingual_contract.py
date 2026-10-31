"""Observed-only bilingual envelopes; no physics, language grammar or gold labels."""
from copy import deepcopy

from . import acceptance_contract as contract


def validate_inputs(inputs):
    """Reject hidden labels rather than merely ignoring extra envelope fields."""
    value = deepcopy(inputs)
    contract.fields(value, ('version', 'episodes'))
    contract.require(value['version'] == 'bilingual-input-v1' and
                     type(value['episodes']) is list and value['episodes'], 'invalid bilingual inputs')
    seen = set()
    for episode in value['episodes']:
        contract.fields(episode, ('id', 'entities', 'anchor', 'context', 'utterances'))
        ids, name = episode['entities'], episode['id']
        contract.require(contract.identifier(name) and name not in seen, 'duplicate or invalid episode')
        seen.add(name)
        contract.require(type(ids) is list and 3 <= len(ids) <= 6 and
            all(contract.identifier(x) and len(x.split()) == 1 for x in ids) and
            len(set(ids)) == len(ids), 'invalid entity roster')
        def reading(bits):
            contract.require(type(bits) is list and len(bits) == len(ids) and
                all(type(v) is int and v in (0, 1) for v in bits), 'complete binary reading required')
        reading(episode['anchor'])
        contract.require(type(episode['context']) is list and 1 <= len(episode['context']) <= 32,
                         'bounded nonempty observed context required')
        for event in episode['context']:
            contract.fields(event, ('action', 'reading'))
            reading(event['reading']); action = event['action']
            contract.require(type(action) is list and len(action) == 4 and
                             all(type(v) is int for v in action), 'invalid native context action')
            kind, first, second, bit = action
            valid = kind == 0 and 0 <= first < len(ids) and 0 <= second < len(ids) and first != second and bit == -1
            valid |= kind == 1 and 0 <= first < len(ids) and second == -1 and bit in (0, 1)
            contract.require(valid, 'invalid native context action')
        contract.require(type(episode['utterances']) is list and 1 <= len(episode['utterances']) <= 5,
                         'bounded nonempty utterance sequence required')
        for event in episode['utterances']:
            contract.fields(event, ('text', 'reading')); reading(event['reading'])
            contract.require(type(event['text']) is str and len(event['text']) <= 512, 'invalid utterance')
            tokens = event['text'].split(); mentions = [token for token in tokens if token in ids]
            contract.require(len(tokens) == 3 and len(mentions) == 2 and len(set(mentions)) == 2,
                             'two distinct grounded mentions and one lexical token required')
    return value

