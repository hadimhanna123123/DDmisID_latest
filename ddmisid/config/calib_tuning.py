"""
Mapping of the calibration samples and MC tunings to their respective years and species for PIDCalib2.
"""

from dataclasses import dataclass, field
from typing import List


class InvalidYearError(Exception):
    """Trigger if invalid year is provided."""

    pass


class YearMixin:
    """Ensure validity of the year key in the queries."""

    valid_years = ["2018", "2017", "2016", "2015", "2012", "2011"]

    def validate_year(self, year: str) -> None:
        """Validate the year key in the query."""
        if year not in self.valid_years:
            raise InvalidYearError(f"Year {year} tuning not supported.")


@dataclass(frozen=True)
class CalibSamples(YearMixin):
    """
    Container dataclass for the calibration samples of interest

    Attributes
    ----------
    hadron_{year}: str
        The calibration sample for the given year, diverging between electrons and hadrons.
    e_{year}: str
        The electron calibration sample for the given year.
    """

    # hadrons, from calibration samples
    hadron_2018: str = "Turbo18"
    hadron_2017: str = "Turbo17"
    hadron_2016: str = "Turbo16"
    hadron_2015: str = "Turbo15"
    hadron_2012: str = "21"
    hadron_2011: str = "21r1"

    # muons, from calibration samples
    muon_2018: str = "Turbo18"
    muon_2017: str = "Turbo17"
    muon_2016: str = "Turbo16"
    muon_2015: str = "Turbo15"
    muon_2012: str = "21"
    muon_2011: str = "21r1"

    # electrons, from calibration samples
    e_2018: str = "Electron18"
    e_2017: str = "Electron17"
    e_2016: str = "Electron16"
    e_2015: str = "Electron15"
    e_2012: str = "21"
    e_2011: str = "21r1"

    def fetch(self, year: str, species: str) -> str:
        """
        Fetch the appropriate calibration sample based on the year and particle type (hadron or electron).

        Parameters
        ----------
        year : str
            The year of the sample (e.g., "2018").
        species : str
            The species type, either 'hadron' or 'e' for electron.

        Returns
        -------
        str
            The calibration sample for the given year and species.

        Raises
        ------
        InvalidYearError
            If an invalid year is provided.
        ValueError
            If an invalid species is provided.
        """
        # validate the year
        self.validate_year(year)

        # validate the species
        match species:
            case "hadron" | "pion" | "kaon" | "proton":
                calib_sample_key = f"hadron_{year}"
            case "muon":
                calib_sample_key = f"muon_{year}"
            case "e" | "electron":
                calib_sample_key = f"e_{year}"
            case _:
                raise ValueError(f"Invalid species {species} provided.")

        # dynamically fetch the calibration sample as per the query parameters
        return getattr(self, calib_sample_key)


@dataclass(frozen=True)
class MCTunings(YearMixin):
    """
    Mapping of the MC tunings to their respective emulated years of data taking.

    Attributes
    ----------
    {year_conditions}: str
    """

    _2018: str = "MC15TuneV1"
    _2017: str = "MC15TuneV1"
    _2016: str = "MC15TuneV1"
    _2015: str = "MC15TuneV1"
    _2012: str = "MC12TuneV4"
    _2011: str = "MC12TuneV4"

    def fetch(self, year: str) -> str:
        """
        Fetch the appropriate MC tuning based on the year.

        Parameters
        ----------
        year : str
            The year of the sample (e.g., "2018").

        Returns
        -------
        str
            The MC tuning for the given year.

        Raises
        ------
        InvalidYearError
            If an invalid year is provided.
        """
        # validate the year
        self.validate_year(year)

        # dynamically fetch the MC tuning as per the query parameters
        return getattr(self, f"_{year}")
