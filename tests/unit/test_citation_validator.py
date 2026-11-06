"""
Unit tests for citation post-validation (app/agents/citation_validator.py).
"""

import pytest

from app.agents.citation_validator import extract_citations_from_text, validate_inline_citations

PAPERS = [
    {"authors": ["Javier Delgado-Lista", "Pablo Perez-Martinez"], "year": 2012},
    {"authors": ["Abdelhamid AS", "Brown TJ", "Thorpe GC"], "year": 2018},
    {"authors": ["Ravinder Nagpal", "Hariom Yadav"], "year": 2018},
    {"authors": ["Willem M de Vos", "Herbert Tilg"], "year": 2022},
]


def flagged(text):
    return validate_inline_citations(text, PAPERS)["unvalidated"]


@pytest.mark.unit
class TestExtraction:
    def test_reads_hyphenated_names_and_several_in_one_parenthesis(self):
        cits = extract_citations_from_text("(Delgado-Lista et al., 2012; Abdelhamid et al., 2018)")
        assert [(c["first_author"], c["year"]) for c in cits] == [("Delgado-Lista", 2012), ("Abdelhamid", 2018)]

    def test_given_name_is_not_read_as_a_particle(self):
        cits = extract_citations_from_text("**3. Ravinder Nagpal et al. (2018)**")
        assert [c["first_author"] for c in cits] == ["Nagpal"]

    def test_reads_particles_two_authors_and_numeric(self):
        cits = extract_citations_from_text("de Vos et al. (2022). Brown and Thorpe (2018) agree [1].")
        assert [(c["first_author"], c["second_author"], c["style"]) for c in cits] == [
            ("de Vos", None, "et_al"), ("Brown", "Thorpe", "two"), (None, None, "numeric")]


@pytest.mark.unit
class TestValidation:
    @pytest.mark.parametrize("text", [
        "(Delgado-Lista et al., 2012)",
        "(Abdelhamid et al., 2018)",          # stored as "Surname Initials"
        "(Thorpe et al., 2018)",              # co-author
        "Brown and Thorpe (2018)",
        "Nagpal et al. (2018)",
        "de Vos et al. (2022)",
    ])
    def test_traceable_citations_pass(self, text):
        assert flagged(text) == 0

    @pytest.mark.parametrize("text", [
        "(Hargreaves et al., 2021)",          # not retrieved
        "(Delgado-Lista et al., 1987)",       # real author, wrong year
        "(Brown and Pemberton, 2018)",        # second author not on the paper
        "Probiotics reduce bloating [1].",    # numeric cannot be traced
    ])
    def test_untraceable_citations_are_flagged(self, text):
        assert flagged(text) == 1

    def test_no_citation_validates_trivially(self):
        result = validate_inline_citations("Protein supports muscle synthesis.", PAPERS)
        assert result["total_citations"] == 0 and result["validation_rate"] == 1.0
