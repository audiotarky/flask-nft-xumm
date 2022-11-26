from setuptools import setup

version = "0.0.2"

with open("requirements.txt") as f:
    required = f.read().splitlines()

setup(
    name="flask_nft_xumm",
    version=version,
    python_requires=">=3.9",
    install_requires=required,
    package_dir={"": "src"},
    package_data={"flask_nft_xumm": ["static/**/*", "templates/*"]},
)
