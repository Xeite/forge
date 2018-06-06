import re

import forge

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use


def test_namespace():
    """
    Keep the namespace clean
    """
    private_ptn = re.compile(r'^\_[a-zA-Z]')
    assert set(filter(private_ptn.match, forge.__dict__.keys())) == set([
        '_compose',
        '_config',
        '_counter',
        '_exceptions',
        '_immutable',
        '_marker',
        '_signature',
        '_utils',
    ])

    public_ptn = re.compile(r'^[a-zA-Z]')
    assert set(filter(public_ptn.match, forge.__dict__.keys())) == set([
        ## Compose
        'Revision',
        # unit
        'delete', 'insert', 'modify', 'translocate', 'move', 'replace',
        # group
        'copy',
        'manage',
        'synthesize', 'sign',
        'sort',
        # other
        'compose',
        'returns',

        ## Signature
        'FSignature',
        'Mapper',
        'fsignature',
        'Factory',
        'FParameter',
        'findparam',
        # variadic
        'VarKeyword', 'kwargs',
        'VarPositional', 'args',
        # context
        'ctx', 'self', 'cls',
        # constructors
        'pos', 'pok', 'arg', 'kwo', 'kwarg', 'vkw', 'vpo',

        ## Config
        'get_run_validators',
        'set_run_validators',

        ## Exceptions
        'ForgeError',
        'ImmutableInstanceError',
        'ForgeError',
        'RevisionError',

        ## Markers
        'empty',
        'void',

        ## Utils
        'callwith',
        'repr_callable',
    ])
