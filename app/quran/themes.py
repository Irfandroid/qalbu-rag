THEMES: dict[str, dict[str, list[str]]] = {
    "kecemasan": {
        "keywords": ["cemas", "takut", "khawatir", "gelisah", "panik"],
        "retrieval_terms": ["ketenangan", "pertolongan", "doa", "kemampuan menghadapi ujian"],
    },
    "kesabaran": {
        "keywords": ["sabar", "ujian", "cobaan", "bertahan"],
        "retrieval_terms": ["kesabaran dalam ujian", "keteguhan", "kemudahan setelah kesulitan"],
    },
    "ketenangan_hati": {
        "keywords": ["tenang", "sakinah", "zikir", "damai"],
        "retrieval_terms": ["mengingat Allah", "hati tenteram", "zikir"],
    },
    "kehampaan": {
        "keywords": [
            "hampa",
            "jampa",
            "kosong",
            "kehilangan arah",
            "tidak bermakna",
            "tak bermakna",
        ],
        "retrieval_terms": [
            "tujuan penciptaan manusia",
            "ibadah",
            "makna hidup",
            "mengingat Allah hati tenteram",
        ],
    },
    "harapan": {
        "keywords": ["harapan", "putus asa", "rahmat", "ampunan"],
        "retrieval_terms": ["jangan berputus asa", "rahmat Allah", "harapan"],
    },
    "kesedihan": {
        "keywords": ["sedih", "duka", "kehilangan", "menangis", "gagal"],
        "retrieval_terms": ["mengadukan kesedihan kepada Allah", "sabar", "harapan"],
    },
    "stres_beban": {
        "keywords": ["beban", "berat", "lelah", "burnout", "tidak sanggup"],
        "retrieval_terms": ["beban sesuai kemampuan", "kesulitan", "pertolongan"],
    },
    "rendah_diri": {
        "keywords": ["minder", "tidak berharga", "rendah diri"],
        "retrieval_terms": ["kemuliaan manusia", "takwa", "nilai diri"],
    },
    "takut_masa_depan": {
        # A generic time word such as "besok" also appears in unrelated market
        # forecasts, so it must not activate a spiritual-anxiety theme by itself.
        "keywords": ["masa depan", "rezeki", "takdir"],
        "retrieval_terms": ["tawakal", "rezeki", "Allah mencukupi"],
    },
    "syukur": {
        "keywords": ["syukur", "nikmat", "bersyukur"],
        "retrieval_terms": ["mengingat Allah", "bersyukur", "karunia"],
    },
    "pengampunan": {
        "keywords": ["ampun", "dosa", "bersalah", "taubat"],
        "retrieval_terms": ["ampunan", "rahmat Allah", "taubat"],
    },
    "hubungan_sosial": {
        "keywords": ["keluarga", "pasangan", "sepi", "sendirian", "sahabat", "teman"],
        "retrieval_terms": ["kedekatan Allah", "persaudaraan", "dukungan manusia"],
    },
    "tawakal": {
        "keywords": ["tawakal", "berserah", "percaya"],
        "retrieval_terms": ["bertawakal kepada Allah", "Allah mencukupi", "usaha"],
    },
    "kekuatan_setelah_hambatan": {
        "keywords": ["kesulitan", "kemudahan", "hikmah"],
        "retrieval_terms": ["bersama kesulitan ada kemudahan", "keteguhan"],
    },
}


def theme_names() -> list[str]:
    return sorted(THEMES)
