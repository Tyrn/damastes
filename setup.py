from setuptools import setup

setup(
    name='Procrustes SmArT',
    version='0.8.2',
    packages=['procr', 'procr.core'],
    entry_points={
        'console_scripts': [
            'pcp = procr.core.pcp:main',
        ]
    },
    install_requires=[
        'mutagen',
    ]
)