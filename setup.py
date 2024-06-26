import setuptools

from ibwpy.constants import IBWPY_VERSION


def _requires_from_file(filename):
    return open(filename).read().splitlines()


setuptools.setup(
    name="ibwpy",
    version=IBWPY_VERSION,
    install_requires=_requires_from_file('requirements.txt'),
    author="Hiroaki Takahashi",
    author_email="aphiloboe@gmail.com",
    description="Edit Igor Pro binary wave files",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
