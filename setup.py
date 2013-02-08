from setuptools import setup

dependencies = [
    'numpy',
    'scipy',
]

project_name = 'NYCBarHop'
project_version = '0.1'
python_version = 'py2.7'

setup(
    name=project_name,
    version=project_version,
    author="George Lewis",
    description=("NYC Bar Hop"),
    license="UNKNOWN",
    install_requires=dependencies,
    classifiers=[
        "Development Status :: 2 - Beta",
    ],
    zip_safe=False,
)
