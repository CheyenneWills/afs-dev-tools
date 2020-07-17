from setuptools import setup, find_packages
setup(
    name="afs-dev-tools",
    version="0.0.1",
    packages=find_packages(),
    scripts=["bin/afs_config_diff"],
    author='Cheyenne Wills',
    author_email='cwills@sinenomine.net',
)