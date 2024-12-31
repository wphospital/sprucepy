import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="sprucepy",
    version="0.2",
    author="Jon Sege",
    author_email="jsege@wphospital.org",
    description="Spruce package",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/wphospital/sprucepy",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'python-crontab',
        'requests',
        'click',
        'pretty_cron',
        'croniter',
        'boto3',
        'psutil',
        'pytz'
    ]
)
