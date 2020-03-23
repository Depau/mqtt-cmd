from setuptools import setup, find_packages

setup(
    name='mqtt-cmd-v2',
    version='0.1',
    packages=find_packages(),
    url='https://gitlab.poul.org/project/mqtt-cmd-v2',
    license='GPLv3.0',
    author='Davide Depau',
    author_email='davide@depau.eu',
    description='Run actions in response to MQTT messages',
    install_requires=['gmqtt', 'pyyaml', 'pyjq', 'aiohttp[speedups]', 'six', 'jinja2'],
    entry_points={
        "console_scripts": [
            "mqtt_cmd = mqtt_cmd:main.main"
        ]
    }
)
