from setuptools import setup, find_packages

version='0.0.1'

setup(
    name='pyperry',
    version=version,
    description='Python library for querying and mapping data through generic '
            'interfaces (this is a port of the Ruby "perry" library)',
    author='Travis Petticrew',
    author_email='travis@petticrew.net',
    maintainer='Travis Petticrew',
    license='MIT',
    url='http://github.com/tpett/pyperry',
    packages=find_packages(exclude=['tests']),
    download_url='http://pypi.python.org/packages/source/p/pyperry/pyperry-%s.tar.gz' % version,
    install_requires=[
        'erlastic==1.0.0',
        'bert==1.0.0',
        'bertrpc>0'
    ],
    classifiers = [
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python'],
)

