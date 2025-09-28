from setuptools import setup, find_packages

setup(
    name="ddmisid",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "numpy",
        "pandas",
        "scipy",
        "awkward",
        "matplotlib",
        "boost-histogram",
        "hist",
        "uproot",
        "iminuit",
        "numba",
        "pyhf",
        "tqdm",
        "tabulate",
        "pyyaml",
        "snakemake",
        "click",
        "SciencePlots",
        "uncertainties",
        "cabinetry",
        "polars",
        "pydantic>=2.0.0",
        "pytest",
        "pyfiglet",
        # "snakemake", # recommended install via mamba and running `pip install -e .` after loading mamba environment
    ],
    entry_points="""
        [console_scripts]
        ddmisid-engine=ddmisid.cli:cli
    """,
)
