#!/usr/bin/env python
"""
Galera Initiator package distribution using Setuptools.
"""


from setuptools import setup, find_packages


setup(
    name='GaleraInitiator',
    version='0.4.0',
    description='Automatically join, bootstrap or recover a Galera cluster.',
    author='Kenny Rasschaert',
    author_email='kenny@kennyrasschaert.be',
    url='https://github.com/rasschaert/galera_initiator',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: System Administrators',
        'Intended Audience :: Developers',
        'Topic :: System :: Clustering',
        'Topic :: Database',
        'Topic :: System :: Systems Administration',
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'galera_init = galera_init:main',
            'galera_status = galera_check:status',
            'galera_seqno = galera_check:seqno',
        ],
    },
)
