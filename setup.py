import setuptools

VERSION = "0.0.535"
PACKAGE_NAME = "gdal2numpy"
AUTHOR = "Valerio Luzzi, Marco Renzi, Lorenzo Borelli"
EMAIL = "valerio.luzzi@gecosistema.com, marco.renzi@gecosistema.com"
GITHUB = f"https://github.com/SaferPlaces2023/{PACKAGE_NAME}.git"
DESCRIPTION = "An utils functions package"

setuptools.setup(
    name=PACKAGE_NAME,
    version=VERSION,
    license='MIT',
    author=AUTHOR,
    author_email=EMAIL,
    description=DESCRIPTION,
    long_description=DESCRIPTION,
    url=GITHUB,
    packages=setuptools.find_packages("src"),
    package_dir={'': 'src'},
    package_data={
        "": ["data/*.json"]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        "setuptools",
        "psutil", 
        "requests", 
        "gdal", 
        "numpy", 
        "boto3", 
        "pyproj", 
        "levenshtein", 
        "xmltodict" 
    ]
)






































































