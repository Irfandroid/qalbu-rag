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
    "kemarahan": {
        "keywords": ["marah", "amarah", "emosi", "jengkel", "kesal"],
        "retrieval_terms": ["menahan amarah", "memaafkan", "berbuat baik"],
    },
    "rasa_bersalah": {
        "keywords": ["bersalah", "menyesal", "rasa bersalah"],
        "retrieval_terms": ["ampunan", "rahmat Allah", "memperbaiki diri"],
    },
    "kegagalan": {
        "keywords": ["gagal", "kegagalan", "tidak berhasil", "jatuh"],
        "retrieval_terms": ["ujian", "keteguhan", "kemudahan setelah kesulitan"],
    },
    "harga_diri": {
        "keywords": ["harga diri", "tidak berharga", "tidak berguna", "nilai diri"],
        "retrieval_terms": ["kemuliaan manusia", "takwa", "nilai diri"],
    },
    "perbandingan": {
        "keywords": ["membandingkan", "dibandingkan", "iri", "kalah dari orang lain"],
        "retrieval_terms": ["kemuliaan manusia", "takwa", "persaudaraan"],
    },
    "malu": {
        "keywords": ["malu", "dipermalukan", "aib"],
        "retrieval_terms": ["menjaga kehormatan", "ampunan", "rahmat Allah"],
    },
    "stres": {
        "keywords": ["stres", "tertekan", "terbebani", "tegang"],
        "retrieval_terms": ["beban sesuai kemampuan", "kesulitan", "pertolongan"],
    },
    "burnout": {
        "keywords": ["burnout", "kelelahan kerja", "habis tenaga", "jenuh"],
        "retrieval_terms": ["kesulitan", "kemudahan", "istirahat"],
    },
    "ketidakpastian": {
        "keywords": ["tidak pasti", "bingung", "ragu", "tidak tahu arah"],
        "retrieval_terms": ["tawakal", "petunjuk", "Allah mencukupi"],
    },
    "kesulitan": {
        "keywords": ["kesulitan", "cobaan", "musibah", "masalah berat"],
        "retrieval_terms": ["sabar", "ujian", "kemudahan setelah kesulitan"],
    },
    "tekanan_finansial_karier": {
        "keywords": ["keuangan", "finansial", "pekerjaan", "karier", "rezeki", "utang"],
        "retrieval_terms": ["rezeki", "usaha", "tawakal", "Allah mencukupi"],
    },
    "kesepian": {
        "keywords": ["kesepian", "sendiri", "ditinggalkan", "tidak punya teman"],
        "retrieval_terms": ["kedekatan Allah", "dukungan manusia", "persaudaraan"],
    },
    "penolakan": {
        "keywords": ["ditolak", "penolakan", "tidak diterima", "tidak diinginkan"],
        "retrieval_terms": ["rahmat Allah", "kemuliaan manusia", "harapan"],
    },
    "konflik": {
        "keywords": ["konflik", "bertengkar", "perselisihan", "bertengkar"],
        "retrieval_terms": ["persaudaraan", "berbuat adil", "berdamai"],
    },
    "patah_hati": {
        "keywords": ["patah hati", "putus cinta", "hubungan berakhir", "sakit hati"],
        "retrieval_terms": ["kesedihan", "sabar", "harapan"],
    },
    "duka": {
        "keywords": ["berduka", "duka", "kehilangan orang", "kematian"],
        "retrieval_terms": ["mengadukan kesedihan kepada Allah", "sabar", "harapan"],
    },
    "tujuan_hidup": {
        "keywords": ["tujuan hidup", "arah hidup", "untuk apa hidup"],
        "retrieval_terms": ["tujuan penciptaan manusia", "ibadah", "makna hidup"],
    },
    "makna_hidup": {
        "keywords": ["makna hidup", "hidup tidak bermakna", "arti hidup"],
        "retrieval_terms": ["tujuan penciptaan manusia", "ibadah", "mengingat Allah"],
    },
    "iman": {
        "keywords": ["iman", "keimanan", "ragu kepada Allah", "jauh dari Allah"],
        "retrieval_terms": ["petunjuk", "mengingat Allah", "keteguhan"],
    },
    "taubat": {
        "keywords": ["taubat", "bertobat", "dosa", "ingin berubah"],
        "retrieval_terms": ["ampunan", "rahmat Allah", "memperbaiki diri"],
    },
    "penerimaan": {
        "keywords": ["menerima keadaan", "sulit menerima", "ikhlas", "berdamai dengan keadaan"],
        "retrieval_terms": ["takdir", "tawakal", "Allah mencukupi"],
    },
}


def theme_names() -> list[str]:
    return sorted(THEMES)
