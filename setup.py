#!/usr/bin/env python
"""
Galera-initiator package distribution using Setuptools.
"""


from setuptools import setup, find_packages


setup(
    name='Galera Initiator',
    version='0.1.0',
    description='Automatically join, bootstrap or recover a Galera cluster.',
    author='Kenny Rasschaert',
    author_email='kenny@kennyrasschaert.be',
    url='https://github.com/rasschaert/galera-initiator',
    license='MIT',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
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
            'galera-initiator = galera-initiator.galera-initiator',
        ],
    },
    install_requires=['netsnmp>=5.5'],
)
