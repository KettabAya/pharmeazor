"""Section extraction across the heading styles real leaflets actually use."""

from pharmeazor.extract.sections import classify_heading, split_sections
from pharmeazor.schemas import Section

RCP_STYLE = """\
4.1. Indications thérapeutiques
Traitement symptomatique des douleurs d'intensité légère à modérée.

4.3. Contre-indications
Hypersensibilité connue à la substance active.
Insuffisance hépatocellulaire sévère.

4.2. Posologie et mode d'administration
Adulte : un comprimé par prise, à renouveler si besoin.

4.5. Interactions avec d'autres médicaments
Associations déconseillées : anticoagulants oraux.
"""

LEAFLET_STYLE = """\
Qu'est-ce que ce médicament et dans quels cas est-il utilisé ?
Ce médicament est un antalgique.

Ne prenez jamais ce médicament
Si vous êtes allergique à la substance active.

Comment prendre ce médicament
Respectez toujours la posologie indiquée.

Autres médicaments et ce médicament
Informez votre pharmacien de tout autre traitement en cours.
"""


class TestHeadingClassification:
    def test_numbered_rcp_heading(self):
        assert classify_heading("4.3. Contre-indications") == Section.CONTRAINDICATIONS

    def test_patient_phrasing(self):
        assert classify_heading("Ne prenez jamais ce médicament") == Section.CONTRAINDICATIONS

    def test_posology_synonyms(self):
        assert classify_heading("Comment prendre ce médicament") == Section.POSOLOGY
        assert classify_heading("Posologie et mode d'administration") == Section.POSOLOGY

    def test_unknown_heading_is_not_guessed(self):
        assert classify_heading("Conservation et date de péremption") is None


class TestSplitting:
    def test_rcp_style_finds_all_four_required(self):
        split = split_sections(RCP_STYLE)
        assert split.coverage == 1.0
        assert split.missing() == []

    def test_leaflet_style_finds_all_four_required(self):
        split = split_sections(LEAFLET_STYLE)
        assert split.coverage == 1.0

    def test_original_sentences_are_preserved(self):
        split = split_sections(RCP_STYLE)
        assert "Insuffisance hépatocellulaire sévère." in split.sections[Section.CONTRAINDICATIONS]

    def test_unrecognised_heading_goes_to_unmapped(self):
        text = RCP_STYLE + "\n6.3. Durée de conservation\n36 mois.\n"
        split = split_sections(text)
        assert any("conservation" in k.lower() for k in split.unmapped)

    def test_missing_section_is_reported(self):
        split = split_sections("4.1. Indications thérapeutiques\nDouleur légère.\n")
        assert Section.POSOLOGY in split.missing()
        assert split.coverage == 0.25
