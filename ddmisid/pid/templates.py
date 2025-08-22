# Factory Interface for Template Makers

from typing import Type, Dict, List, Union
from abc import ABC, abstractmethod
import hist
import pickle
from pathlib import Path
import boost_histogram as bh


def save_histogram(
    binning: Dict[str, List[float]],
    hist: Union[hist.Hist, bh.Histogram],
    species: str,
    path: Union[str, None] = None,
):
    """Generalized helper function to save multi-dimensional histograms."""

    # Retrieve binning keys and assert there are at least 3 dimensions
    binning_keys = list(binning.keys())
    num_dimensions = len(binning_keys)

    # Recursive helper function to traverse the binning dimensions
    def traverse_binning(binning_indices, current_index=0, directory=""):
        if current_index < num_dimensions:  # Keep traversing dimensions
            bin_key = binning_keys[current_index]
            for i, bin_value in enumerate(binning[bin_key]):
                if i < len(binning[bin_key]) - 1:
                    new_directory = f"{directory}/{bin_value}-{binning[bin_key][i+1]}"
                    traverse_binning(
                        binning_indices + [i], current_index + 1, new_directory
                    )
        else:  # When all dimensions have been traversed, save the histogram
            Path(directory).mkdir(parents=True, exist_ok=True)
            # Index into the histogram using the binning indices collected so far
            with open(f"{directory}/{species}.pkl", "wb") as file:
                pickle.dump(hist[tuple(binning_indices) + (...,)], file)

    # Start traversal from the first dimension
    traverse_binning([], 0, path)


class Template(ABC):
    """
    Abstract base class for creating templates from PID efficiency histograms.
    All template makers must implement the make_hist and save_templates methods.
    """

    @abstractmethod
    def make_hist(self) -> [hist.Hist, bh.Histogram]:
        """Create a histogram from efficiency values."""
        pass

    @abstractmethod
    def save_hist(
        self, binning: Dict[str, List[float]], path: Union[str, None] = None
    ) -> None:
        """Save histograms to files."""
        pass


class BinnedTemplate(Template):
    """
    Template class for creating binned templates from PID efficiency histograms.
    """

    def __init__(
        self, path_prefix: str, species: str, reco_categories: List[str]
    ) -> None:
        self.species = species  # e.g. `kaon`
        self.template_bins = [f"{species}_to_{recocat}" for recocat in reco_categories]
        self.path_prefix = path_prefix
        self.eff_hists = self._get_eff_hists(f"{self.path_prefix}/{species}")
        self.hist = None

    def _get_eff_hists(
        self, species_path: str, efficiency_file: str = "processed_perf.pkl"
    ) -> Dict[str, Union[hist.Hist, bh.Histogram]]:
        """Source the PID efficiency histograms for the given species."""
        eff_hists_dict = {}
        for reco in self.template_bins:
            eff_hists_dict[reco] = self._open_eff_hist(
                f"{species_path}/{reco}/{efficiency_file}"
            )
        return eff_hists_dict

    def _open_eff_hist(self, eff_hist_path: str) -> Union[hist.Hist, bh.Histogram]:
        """Load the efficiency histogram from the given path."""
        with open(eff_hist_path, "rb") as file:
            return pickle.load(file)

    def make_hist(self) -> Union[hist.Hist, bh.Histogram]:
        """Create and fill the histogram with efficiency data."""
        hist_axes = [axis for axis in self.eff_hists[self.template_bins[0]].axes]
        hist_axes.append(
            hist.axis.StrCategory(
                self.template_bins, name="reco_cuts", label="reco cuts"
            )
        )
        self.hist = hist.Hist(*hist_axes, storage=hist.storage.Weight())

        for reco, eff_hist in self.eff_hists.items():
            if reco not in self.template_bins:
                raise ValueError(f"{reco} is not a valid category value")
            elif len(hist_axes) - 1 == 2:
                self.hist[:, :, reco] = eff_hist.view()
            elif len(hist_axes) - 1 == 3:
                self.hist[:, :, :, reco] = eff_hist.view()
            else:
                raise ValueError("Inappropriate binning dimensions")
        return self.hist

    def save_hist(
        self, binning: Dict[str, List[float]], path: Union[str, None] = "templates"
    ) -> None:
        """Save the templates based on the binning structure."""

        assert (
            self.hist is not None
        ), "Must run make_hist method before saving templates"
        # based on binning variables, save histogram with n_binning_vars + reco categorical axis

        save_histogram(binning, self.hist, self.species, path)

    def __str__(self) -> str:
        return f"BinnedTemplate(species={self.species}, hist={self.hist})"


class TemplateFactory:
    """
    Simplified factory class to dynamically create BinnedTemplate instances based on species.
    Allows registering species dynamically.
    """

    def __init__(self, default_template_class: Type[Template] = BinnedTemplate) -> None:
        """
        Initialize the factory with a default template class.
        """
        self._creators = {}  # Dictionary to map species to template classes
        self.default_template_class = default_template_class

    def register_species(
        self, species: str, template_class: Type[Template] = None
    ) -> None:
        """
        Register a species and its corresponding template class.
        If no class is provided, the default template class is used.
        """
        if template_class is None:
            template_class = self.default_template_class
        self._creators[species] = template_class

    def fetch_template_maker(
        self, species: str, path_prefix: str, reco_categories: List[str]
    ) -> Template:
        """
        Create a template instance for the given species.
        """
        template_class = self._creators.get(species, self.default_template_class)
        return template_class(path_prefix, species, reco_categories)

    def list_registered_species(self) -> List[str]:
        """Return a list of all registered species."""
        return list(self._creators.keys())
