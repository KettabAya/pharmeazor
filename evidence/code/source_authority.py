# ==========================================
# PHARMEAZOR - SOURCE AUTHORITY
# ==========================================
SOURCE_AUTHORITY = {

    "Ministère_industrie_Pharmaceutique": {
        "url": "https://www.miph.gov.dz/fr/",
        "sub_urls": {
             "url": "https://www.miph.gov.dz/fr/nomenclature-nationale-des-produits-pharmaceutiques/",
        },
        "authority_level": 1,
        "authority_type": "Official Algerian nomenclature",
        "country": "Algeria"
    },
    "PharmNet": {
        "url": "https://pharmnet-dz.com/",
        "sub_urls": {
        },
        "authority_level": 2,
        "authority_type": "professional_medical_platform",
        "country": "Algeria"
    },
    "MEDAlgérie": {
        "url": "https://www.medal-dz.com/",
        "sub_urls": {
        },
        "authority_level": 2,
        "authority_type": "professional_medical_platform",
        "country": "Algeria"
    },
    "dzair-pharma.net": {
        "url": "https://www.dzair-pharma.net/",
        "sub_urls": {
            "url": "https://www.dzair-pharma.net/recherche/",
        },
        "authority_level": 2,
        "authority_type": "professional_medical_platform",
        "country": "Algeria"
    },
    "ANPP": {
        "url": "https://rcp.anpp.dz/",
        "sub_urls": {
         
        },
        "authority_level": 1,
        "authority_type": "Autorité_réglementaire_nationale",
        "country": "Algeria"
    },
    "DailyMed": {
        "url": "https://dailymed.nlm.nih.gov/dailymed/",
        "sub_urls": {
            
        },
        "authority_level": 3,
        "authority_type": "Organisme_public_américain",
        "country": "United_States"
    },
    "EMA": {
        "url": "https://www.ema.europa.eu/en",
        "sub_urls": {
           
        },
        "authority_level": 3,
        "authority_type": "Organisme_public_européen",
        "country": "European_Union"
    },
    "ANSM": {
        "url": "https://ansm.sante.fr/",
        "sub_urls": {
         
        },
        "authority_level": 3,
        "authority_type": "Organisme_public_français",
        "country": "France"
    },
    "TGA": {
    "url": "https://www.tga.gov.au/",
    "sub_urls": [
        {
           
            "url": "https://www.tga.gov.au/resources/cancellations-by-sponsors/enalapril-enalapril-maleate-20mg-tablet-blister-pack-cancelled-under-section-301c-act-0",
          
        }
    ],
    "authority_level": 3,
    "authority_type": "National_Regulatory_Authority",
    "country": "Australia"
},
    "MHRA": {
    "url": "https://products.mhra.gov.uk/",
    "sub_urls": [
        {
            
        }
    ],
    "authority_level": 3,
    "authority_type": "National_Regulatory_Authority",
    "country": "United_Kingdom"
}
}
# ==========================================
# GET SOURCE INFORMATION
# ==========================================

def get_source_authority(source_name):

    source = SOURCE_AUTHORITY.get(source_name)

    if source is None:
        return None

    return {
        "source_name": source_name,
        **source
    }


# ==========================================
# GET ALL SOURCES
# ==========================================

def get_all_sources():

    return [
        get_source_authority(name)
        for name in SOURCE_AUTHORITY
    ]