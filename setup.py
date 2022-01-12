import setuptools

setuptools.setup(
    name="reparsec",
    version="0.1.0",
    license="MIT License",
    author="ethframe",
    description="Parser combinators library with error recovery",
    url="https://github.com/ethframe/reparsec",
    packages=setuptools.find_packages(exclude=["tests"]),
    zip_safe=False,
)
