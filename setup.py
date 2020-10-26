from setuptools import setup

setup(
    name='jencli',
    version='0.0.1',
    py_modules=['jencli'],
    install_requires=[
        'click',
        'colorama',
        'jenkins'
    ],
    entry_points='''
        [console_scripts]
        jencli=jencli:cli
    ''',
)
