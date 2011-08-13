from setuptools import setup,find_packages

setup(
    name='rambler.net',
    version = '2.0',
    description='Rambler extension for common network operations',
    author='Scott Robertson',
    author_email='srobertson@codeit.com',
    #package_dir = {'': 'src'},
    packages = find_packages(),
    install_requires = ['Rambler', 'webob', 'routes','kid']
    

)
