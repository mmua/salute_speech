#!/usr/bin/env python

"""Setup file"""

# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open('README.md', encoding="utf-8") as readme_file:
    readme = readme_file.read()

requirements = [
    'Click==8.1.7',
    'python-dotenv==1.0.0',
    'requests==2.31.0',
    'pydub==0.25.1'
]

setup(
    name='salute_speech',
    version='1.0.0',
    description="Sber Salute Speech API",
    long_description=readme,
    author="Maxim Moroz",
    author_email='mimoroz@edu.hse.ru',
    url='https://github.com/mmua/salute_speech',
    packages=find_packages(include=['salute_speech', 'salute_speech.*'], ),
    package_data={
        'salute_speech': ['conf/*'],  # include conf files in webinar package
    },
    entry_points={
        'console_scripts': [
            'salute_speech=salute_speech:cli'
        ]
    },
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    keywords='speech',
    classifiers=[
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.8',
    ]
)
