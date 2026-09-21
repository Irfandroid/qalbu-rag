THEMES: dict[str, dict[str, list[str]]] = {
    "kecemasan": {"keywords": ["cemas", "takut", "khawatir", "gelisah", "panik"]},
    "kesabaran": {"keywords": ["sabar", "ujian", "cobaan", "bertahan"]},
    "ketenangan_hati": {"keywords": ["tenang", "sakinah", "zikir", "damai"]},
    "kehampaan": {
        "keywords": [
            "hampa",
            "jampa",
            "kosong",
            "kehilangan arah",
            "tidak bermakna",
            "tak bermakna",
        ]
    },
    "harapan": {"keywords": ["harapan", "putus asa", "rahmat", "ampunan"]},
    "kesedihan": {"keywords": ["sedih", "duka", "kehilangan", "menangis"]},
    "stres_beban": {"keywords": ["beban", "berat", "lelah", "burnout"]},
    "rendah_diri": {"keywords": ["minder", "tidak berharga", "rendah diri"]},
    "takut_masa_depan": {"keywords": ["masa depan", "rezeki", "takdir", "besok"]},
    "syukur": {"keywords": ["syukur", "nikmat", "bersyukur"]},
    "pengampunan": {"keywords": ["ampun", "dosa", "bersalah", "taubat"]},
    "hubungan_sosial": {"keywords": ["keluarga", "pasangan", "sepi", "sahabat"]},
    "tawakal": {"keywords": ["tawakal", "berserah", "percaya"]},
    "kekuatan_setelah_hambatan": {"keywords": ["kesulitan", "kemudahan", "hikmah"]},
}


def theme_names() -> list[str]:
    return sorted(THEMES)
