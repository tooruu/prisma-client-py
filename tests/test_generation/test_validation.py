import re
import subprocess

import pytest

from prisma.utils import temp_env_update
from ..utils import Testdir


def assert_no_generator_output(output: str) -> None:
    # as we run generation under coverage we need to remove any warnings
    # for example, coverage.py will warn that the tests module was not imported
    output = re.sub(r'.* prisma:GeneratorProcess Coverage.py warning:.*', '', output)
    assert 'prisma:GeneratorProcess' not in output


def test_field_name_basemodel_attribute(testdir: Testdir) -> None:
    """Field name shadowing a basemodel attribute is not allowed"""
    schema = (
        testdir.SCHEMA_HEADER
        + '''
        model User {{
            id   String @id
            json String
        }}
    '''
    )
    with pytest.raises(subprocess.CalledProcessError) as exc:
        testdir.generate(schema=schema)

    assert (
        'Field name "json" shadows a BaseModel attribute; '
        'use a different field name with \'@map("json")\''
        in str(exc.value.output, 'utf-8')
    )


def test_field_name_python_keyword(testdir: Testdir) -> None:
    """Field name shadowing a python keyword is not allowed"""
    schema = (
        testdir.SCHEMA_HEADER
        + '''
        model User {{
            id   String @id
            from String
        }}
    '''
    )
    with pytest.raises(subprocess.CalledProcessError) as exc:
        testdir.generate(schema=schema)

    assert (
        'Field name "from" shadows a Python keyword; use a different field name with \'@map("from")\''
        in str(exc.value.output, 'utf-8')
    )


def test_field_name_prisma_not_allowed(testdir: Testdir) -> None:
    """Field name "prisma" is not allowed as it overrides our own method"""
    schema = (
        testdir.SCHEMA_HEADER
        + '''
        model User {{
            id     String @id
            prisma String
        }}
    '''
    )
    with pytest.raises(subprocess.CalledProcessError) as exc:
        testdir.generate(schema=schema)

    assert (
        'Field name "prisma" shadows a Prisma Client Python method; '
        'use a different field name with \'@map("prisma")\''
    ) in str(exc.value.output, 'utf-8')


def test_unknown_type(testdir: Testdir) -> None:
    """Unsupported scalar type is not allowed"""
    schema = '''
        datasource db {{
          provider = "postgres"
          url      = env("POSTGRES_URL")
        }}

        generator db {{
          provider = "coverage run -m prisma"
          output = "{output}"
          {options}
        }}

        model User {{
            id   String @id
            meta Bytes
        }}
    '''
    with pytest.raises(subprocess.CalledProcessError) as exc:
        testdir.generate(schema=schema)

    assert 'Unsupported scalar field type: Bytes' in str(exc.value.output, 'utf-8')


def test_native_binary_target_no_warning(testdir: Testdir) -> None:
    """binaryTargets only being native does not raise warning"""
    with temp_env_update({'PRISMA_PY_DEBUG': '0'}):
        result = testdir.generate(options='binaryTargets = ["native"]')

    stdout = result.stdout.decode('utf-8')
    assert 'Warning' not in stdout
    assert 'binaryTargets option' not in stdout
    assert_no_generator_output(stdout)


def test_binary_targets_warning(testdir: Testdir) -> None:
    """Binary targets option being present raises a warning"""
    with temp_env_update({'PRISMA_PY_DEBUG': '0'}):
        result = testdir.generate(
            options='binaryTargets = ["native", "rhel-openssl-1.1.x"]'
        )

    stdout = result.stdout.decode('utf-8')
    assert_no_generator_output(stdout)
    assert (
        'Warning: The binaryTargets option '
        'is not currently supported by Prisma Client Python' in stdout
    )


@pytest.mark.parametrize(
    'http,new',
    [
        ('aiohttp', 'asyncio'),
        ('requests', 'sync'),
    ],
)
def test_old_http_option(testdir: Testdir, http: str, new: str) -> None:
    """A helpful error is raised if the old http config option is used"""
    with pytest.raises(subprocess.CalledProcessError) as exc:
        testdir.generate(options=f'http = "{http}"')

    stdout = exc.value.stdout.decode('utf-8')
    assert (
        'The http option has been removed '
        'in favour of the interface option.' in stdout
    )
    assert (
        'Please remove the http option from '
        'your Prisma schema and replace it with:' in stdout
    )
    assert f'interface = "{new}"' in stdout
