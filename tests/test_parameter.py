import inspect
from unittest.mock import Mock

import pytest

import forge._immutable as immutable
from forge._marker import void
import forge._parameter
from forge._parameter import (
    Factory,
    FParameter,
    VarPositional,
    VarKeyword,
    _default_or_factory,
    cls_,
    self_,
)
from forge._signature import CallArguments

# pylint: disable=C0103, invalid-name
# pylint: disable=R0201, no-self-use
# pylint: disable=W0212, protected-access

empty = inspect.Parameter.empty

dummy_converter = lambda ctx, name, value: (ctx, name, value)
dummy_validator = lambda ctx, name, value: None

FPARAM_DEFAULTS = dict(
    name=None,
    interface_name=None,
    default=inspect.Parameter.empty,
    type=inspect.Parameter.empty,
    converter=None,
    validator=None,
    is_contextual=False
)

FPARAM_POS_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_ONLY,
    is_contextual=False,
)

FPARAM_POK_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    is_contextual=False,
)

FPARAM_CTX_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.POSITIONAL_OR_KEYWORD,
    is_contextual=True,
    default=empty,
    converter=None,
    validator=None,
)

FPARAM_VPO_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.VAR_POSITIONAL,
    is_contextual=False,
    default=empty,
    type=empty,
)

FPARAM_KWO_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.KEYWORD_ONLY,
    is_contextual=False,
)

FPARAM_VKW_DEFAULTS = dict(
    FPARAM_DEFAULTS,
    kind=inspect.Parameter.VAR_KEYWORD,
    is_contextual=False,
    default=empty,
    type=empty,
)


class TestFactory:
    def test_meta(self):
        assert issubclass(Factory, immutable.Immutable)

    def test__repr__(self):
        def func():
            pass
        assert repr(Factory(func)) == '<Factory {}>'.format(func.__qualname__)

    def test__call__(self):
        mock = Mock()
        factory = Factory(mock)
        factory()
        mock.assert_called_once_with()


dummy_func = lambda: None

@pytest.mark.parametrize(('default', 'factory', 'result'), [
    pytest.param(1, void, 1, id='default'),
    pytest.param(void, dummy_func, Factory(dummy_func), id='factory'),
    pytest.param(void, void, inspect.Parameter.empty, id='neither'),
    pytest.param(1, dummy_func, None, id='both'),
])
def test_default_or_factory(default, factory, result):
    if result is not None:
        assert _default_or_factory(default, factory) == result
        return

    with pytest.raises(TypeError) as excinfo:
        _default_or_factory(default, factory)
    assert excinfo.value.args[0] == \
        'expected either "default" or "factory", received both'


class TestFParameter:
    # pylint: disable=E1101, no-member
    def test__init__default_or_factory(self):
        fparam = FParameter(
            inspect.Parameter.POSITIONAL_ONLY,
            factory=dummy_func,
        )
        assert isinstance(fparam.default, Factory)
        assert fparam.default.factory == dummy_func

    @pytest.mark.parametrize(('kwargs', 'expected'), [
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': None,
                'interface_name': None,
            },
            '<missing>',
            id='name_missing',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
            },
            'a',
            id='named',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
                'default': None,
            },
            'a=None',
            id='named_default',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'a',
                'type': int,
            },
            'a:int',
            id='named_type',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'b',
            },
            'a->b',
            id='named_mapping',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.POSITIONAL_ONLY,
                'name': 'a',
                'interface_name': 'b',
                'default': None,
                'type': int,
            },
            'a->b:int=None',
            id='named_mapping_anotation_default',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.VAR_POSITIONAL,
                'name': 'a',
                'interface_name': 'a',
            },
            '*a',
            id='var_positional',
        ),
        pytest.param(
            {
                'kind': inspect.Parameter.VAR_KEYWORD,
                'name': 'a',
                'interface_name': 'a',
            },
            '**a',
            id='var_keyword',
        ),
    ])
    def test__str__and__repr__(self, kwargs, expected):
        fparam = FParameter(**kwargs)
        assert str(fparam) == expected
        assert repr(fparam) == '<FParameter "{}">'.format(expected)

    @pytest.mark.parametrize(('in_', 'out_'), [
        pytest.param(void, 1, id='void'),
        pytest.param(0, 0, id='value'),
    ])
    def test_apply_default(self, in_, out_):
        fparam = FParameter(inspect.Parameter.POSITIONAL_ONLY, default=1)
        assert fparam.apply_default(in_) == out_

    def test_apply_default_factory(self):
        mock = Mock()
        fparam = FParameter(
            inspect.Parameter.POSITIONAL_ONLY,
            default=Factory(mock),
        )
        assert fparam.apply_default(void) == mock.return_value

    @pytest.mark.parametrize(('converter', 'in_', 'to_out_'), [
        pytest.param(
            lambda ctx, name, value: (ctx, name, value),
            ('context', 'name', 1),
            lambda in_: in_,
            id='unit',
        ),
        pytest.param(
            [lambda ctx, name, value: (ctx, name, value) for i in range(2)],
            ('context', 'name', 1),
            lambda in_: tuple([*in_[0:2], in_]),
            id='list',
        ),
        pytest.param(
            None,
            ('context', 'name', 1),
            lambda in_: in_[2],
            id='none',
        ),
    ])
    def test_apply_conversion(self, converter, in_, to_out_):
        fparam = FParameter(
            inspect.Parameter.POSITIONAL_ONLY,
            converter=converter,
        )
        assert fparam.apply_conversion(*in_) == to_out_(in_)

    @pytest.mark.parametrize(('has_validation',), [(True,), (False,)])
    def test_apply_validation(self, has_validation):
        called_with = None
        def validator(*args, **kwargs):
            nonlocal called_with
            called_with = CallArguments(*args, **kwargs)

        fparam = FParameter(
            inspect.Parameter.POSITIONAL_ONLY,
            validator=validator if has_validation else None,
        )
        args = ('context', 'name', 'value')
        fparam.apply_validation(*args)
        if has_validation:
            assert called_with.args == args
        else:
            assert called_with is None

    def test__call__(self):
        mock_default = Mock()
        default = Factory(mock_default)
        converter = Mock()
        validator = Mock()
        fparam = FParameter(
            inspect.Parameter.POSITIONAL_ONLY,
            default=default,
            converter=converter,
            validator=validator,
        )
        in_ = (object(), object(), void)
        assert fparam(*in_) == converter.return_value
        validator.assert_called_once_with(*in_[0:2], converter.return_value)
        converter.assert_called_once_with(*in_[0:2], mock_default.return_value)
        mock_default.assert_called_once_with()

    @pytest.mark.parametrize(('rkey', 'rval'), [
        pytest.param('kind', inspect.Parameter.KEYWORD_ONLY, id='kind'),
        pytest.param('default', 1, id='default'),
        pytest.param('factory', dummy_func, id='factory'),
        pytest.param('type', int, id='type'),
        pytest.param('name', 'b', id='name'),
        pytest.param('interface_name', 'b', id='interface_name'),
        pytest.param('converter', dummy_converter, id='converter'),
        pytest.param('validator', dummy_validator, id='validator'),
    ])
    def test_replace(self, rkey, rval):
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=None,
            interface_name=None,
            default=None,
        )
        # pylint: disable=E1101, no-member
        fparam2 = fparam.replace(**{rkey: rval})
        for k, v in immutable.asdict(fparam2).items():
            if k in ('name', 'interface_name') and \
                rkey in ('name', 'interface_name'):
                v = rval
            elif k == 'default' and rkey == 'factory':
                v = Factory(dummy_func)
            assert getattr(fparam2, k) == v

    def test_parameter(self):
        kwargs = dict(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name='a',
            interface_name='b',
            default=None,
            type=int,
        )
        param = FParameter(**kwargs).parameter
        assert param.kind == kwargs['kind']
        assert param.name == kwargs['name']
        assert param.default == kwargs['default']
        assert param.annotation == kwargs['type']

    def test_parameter_wo_names_raises(self):
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            fparam.parameter
        assert excinfo.value.args[0] == 'Cannot generate an unnamed parameter'

    def test_interface_parameter(self):
        kwargs = dict(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name='a',
            interface_name='b',
            default=None,
            type=int,
        )
        param = FParameter(**kwargs).interface_parameter
        assert param.kind == kwargs['kind']
        assert param.name == kwargs['interface_name']
        assert param.default == kwargs['default']
        assert param.annotation == kwargs['type']

    def test_interface_parameter_wo_names_raises(self):
        fparam = FParameter(
            kind=inspect.Parameter.POSITIONAL_ONLY,
            name=None,
            interface_name=None,
        )
        with pytest.raises(TypeError) as excinfo:
            # pylint: disable=W0104, pointless-statement
            fparam.interface_parameter
        assert excinfo.value.args[0] == 'Cannot generate an unnamed parameter'

    def test_defaults(self):
        fparam = FParameter(inspect.Parameter.POSITIONAL_ONLY)
        assert fparam.kind == inspect.Parameter.POSITIONAL_ONLY
        for k, v in FPARAM_DEFAULTS.items():
            assert getattr(fparam, k) == v

    def test_from_parameter(self):
        kwargs = dict(
            name='a',
            kind=inspect.Parameter.POSITIONAL_ONLY,
            annotation=int,
            default=3,
        )
        param = inspect.Parameter(**kwargs)
        fparam = FParameter.from_parameter(param)
        for k, v in dict(
                FPARAM_DEFAULTS,
                kind=kwargs['kind'],
                name=kwargs['name'],
                interface_name=kwargs['name'],
                type=kwargs['annotation'],
                default=kwargs['default'],
            ).items():
            assert getattr(fparam, k) == v

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='name',
        ),
        pytest.param(
            {'name': 'a', 'interface_name': 'b'},
            {'name': 'a', 'interface_name': 'b'},
            id='name_and_interface_name',
        ),
        pytest.param(
            {'default': 1},
            {'default': 1},
            id='default',
        ),
        pytest.param(
            {'factory': dummy_func},
            {'default': Factory(dummy_func)},
            id='factory',
        ),
    ])
    def test_create_positional_only(self, extra_in, extra_out):
        kwargs = dict(
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_positional_only(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_POS_DEFAULTS, **kwargs, **extra_out}

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='name',
        ),
        pytest.param(
            {'name': 'a', 'interface_name': 'b'},
            {'name': 'a', 'interface_name': 'b'},
            id='name_and_interface_name',
        ),
        pytest.param(
            {'default': 1},
            {'default': 1},
            id='default',
        ),
        pytest.param(
            {'factory': dummy_func},
            {'default': Factory(dummy_func)},
            id='factory',
        ),
    ])
    def test_create_positional_or_keyword(self, extra_in, extra_out):
        kwargs = dict(
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_positional_or_keyword(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_POK_DEFAULTS, **kwargs, **extra_out}

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {}, {'name': None, 'interface_name': None}, id='no_names'
        ),
        pytest.param(
            {'interface_name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='interface_name',
        ),
        pytest.param(
            {'name': 'a'},
            {'name': 'a', 'interface_name': 'a'},
            id='name',
        ),
        pytest.param(
            {'name': 'a', 'interface_name': 'b'},
            {'name': 'a', 'interface_name': 'b'},
            id='name_and_interface_name',
        ),
    ])
    def test_create_contextual(self, extra_in, extra_out):
        kwargs = dict(type=int)
        fparam = FParameter.create_contextual(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_CTX_DEFAULTS, **kwargs, **extra_out}

    def test_create_var_positional(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_var_positional(**kwargs)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VPO_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    @pytest.mark.parametrize(('extra_in', 'extra_out'), [
        pytest.param(
            {'default': 1},
            {'default': 1},
            id='default',
        ),
        pytest.param(
            {'factory': dummy_func},
            {'default': Factory(dummy_func)},
            id='factory',
        ),
    ])
    def test_create_keyword_only(self, extra_in, extra_out):
        kwargs = dict(
            interface_name='a',
            name='b',
            type=int,
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_positional_or_keyword(**kwargs, **extra_in)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == \
            {**FPARAM_POK_DEFAULTS, **kwargs, **extra_out}

    def test_create_var_keyword(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        fparam = FParameter.create_var_keyword(**kwargs)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VKW_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )


class TestVarPositional:
    @staticmethod
    def assert_iterable_and_get_fparam(varp):
        varplist = list(varp)
        assert len(varplist) == 1
        return varplist[0]

    def test_new(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        varp = VarPositional()(**kwargs)
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VPO_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test__call__(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        varp = VarPositional(**kwargs)
        fparam = self.assert_iterable_and_get_fparam(varp)
        assert isinstance(fparam, FParameter)
        assert immutable.asdict(fparam) == dict(
            FPARAM_VPO_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

class TestVarKeyword:
    @staticmethod
    def assert_mapping_and_get_fparam(vark):
        varklist = list(vark.items())
        assert len(varklist) == 1
        return varklist[0]

    def test_new(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        vark = VarKeyword(**kwargs)
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert isinstance(fparam, FParameter)
        assert name == kwargs['name']
        assert immutable.asdict(fparam) == dict(
            FPARAM_VKW_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test__call__(self):
        kwargs = dict(
            name='b',
            converter=dummy_converter,
            validator=dummy_validator,
        )
        vark = VarKeyword()(**kwargs)
        name, fparam = self.assert_mapping_and_get_fparam(vark)
        assert isinstance(fparam, FParameter)
        assert name == kwargs['name']
        assert immutable.asdict(fparam) == dict(
            FPARAM_VKW_DEFAULTS,
            name=kwargs['name'],
            interface_name=kwargs['name'],
            converter=kwargs['converter'],
            validator=kwargs['validator'],
        )

    def test_mapping(self):
        vark = VarKeyword()
        assert vark.name in vark
        assert '{}_'.format(vark.name) not in vark
        assert len(vark) == 1
        assert list(vark) == [vark.name]


class TestConvenience:
    def test_constructors(self):
        # pylint: disable=E1101, no-member
        for conv, method in [
                ('pos', FParameter.create_positional_only),
                ('arg', FParameter.create_positional_or_keyword),
                ('ctx', FParameter.create_contextual),
                ('kwarg', FParameter.create_keyword_only),
            ]:
            assert getattr(forge._parameter, conv) == method

    def test_self_(self):
        assert isinstance(self_, FParameter)
        assert immutable.asdict(self_) == dict(
            FPARAM_CTX_DEFAULTS,
            name='self',
            interface_name='self',
        )

    def test_cls_(self):
        assert isinstance(cls_, FParameter)
        assert immutable.asdict(cls_) == dict(
            FPARAM_CTX_DEFAULTS,
            name='cls',
            interface_name='cls',
        )

    def test_args(self):
        args = forge._parameter.args
        assert isinstance(args, VarPositional)
        assert args.name == 'args'
        assert args.converter is None
        assert args.validator is None

    def test_kwargs(self):
        kwargs = forge._parameter.kwargs
        assert isinstance(kwargs, VarKeyword)
        assert kwargs.name == 'kwargs'
        assert kwargs.converter is None
        assert kwargs.validator is None