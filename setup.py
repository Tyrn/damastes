from setuptools import setup

setup(
    name='Procrustes SmArT',
    version='0.8.0',
    packages=['procr.core'],
    entry_points={
        'console_scripts': [
            'pcp = procr.core.pcp:main',
        ]
    },
    install_requires=[
        'mutagen',
    ]
)