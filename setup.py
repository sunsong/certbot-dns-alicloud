import os
import sys

from setuptools import find_packages
from setuptools import setup

version = '0.0.2'

install_requires = [
    'aliyun-python-sdk-core>=2.13.15',
    'aliyun-python-sdk-alidns>=2.0.18',
    'setuptools>=39.0.1',
]

if not os.environ.get('SNAP_BUILD'):
    install_requires.extend([
        # We specify the minimum acme and certbot version as the current plugin
        # version for simplicity.
        f'acme>=1.0.0',
        f'certbot>=1.0.0',
    ])
elif 'bdist_wheel' in sys.argv[1:]:
    raise RuntimeError('Unset SNAP_BUILD when building wheels '
                       'to include certbot dependencies.')
if os.environ.get('SNAP_BUILD'):
    install_requires.append('packaging')

docs_extras = [
    'Sphinx>=1.0',  # autodoc_member_order = 'bysource', autodoc_default_flags
    'sphinx_rtd_theme',
]

setup(
    name='certbot-dns-alicloud',
    version=version,
    description="AliCloud DNS Authenticator plugin for Certbot",
    url='https://github.com/certbot/certbot',
    author="Jules",
    author_email='certbot-dev@eff.org',
    license='Apache License 2.0',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Security',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Networking',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],

    packages=find_packages(),
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        'docs': docs_extras,
    },
    entry_points={
        'certbot.plugins': [
            'dns-alicloud = certbot_dns_alicloud._internal.dns_alicloud:Authenticator',
        ],
    },
)
