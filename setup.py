import setuptools
setuptools.setup(
    name = "porntool",
    version = "0.1",
    packages = setuptools.find_packages(),
    install_requires = ['SQLAlchemy>=0.9.4', 'urwid>=1.2.1'],
    extras_require = {'rating': ['numpy', 'scipy']}
)
