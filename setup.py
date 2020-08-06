from setuptools import find_packages, setup

setup(
    name='pdf-service',
    version='1.0.0',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'flask == 1.1.2',
        'weasyprint == 51',
        'elastic-apm[flask] == 5.8.1'
    ],
)
