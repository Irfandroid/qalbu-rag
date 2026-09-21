"""Reviewed Indonesian working summaries for selected community Arabic tafsir.

These are retrieval aids, not official translations and never replace the
original Arabic tafsir shown to the user.
"""

TAFSIR_SUMMARIES_ID: dict[str, str] = {
    "quran-com-en-013-028": (
        "Tafsir menjelaskan bahwa hati memperoleh ketenteraman dengan mengingat "
        "Allah melalui tasbih, tahmid, membaca dan mendengarkan Al-Qur'an, serta "
        "bentuk zikir lainnya."
    ),
}

TAFSIR_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "quran-com-en-013-028": ("tasbih", "tahmid", "membaca", "mendengarkan"),
}

TAFSIR_UNSUPPORTED_MARKERS: dict[str, tuple[str, ...]] = {
    "quran-com-en-013-028": ("sujud", "doa", "puasa", "berpuasa", "tanda-tanda"),
}

SAFE_REFLECTIONS_ID: dict[str, str] = {
    "quran-com-en-013-028": (
        "Rasa hampa bisa membuat hari terasa kehilangan arah; perasaan itu layak "
        "diakui tanpa buru-buru dihakimi. Ayat yang ditemukan mengarahkan hati "
        "pada mengingat Allah sebagai jalan menuju ketenteraman, bukan sebagai "
        "janji hilangnya rasa hampa secara instan. Dalam tafsir yang tersedia, "
        "mengingat Allah mencakup tasbih, tahmid, membaca dan mendengarkan "
        "Al-Qur'an, serta bentuk zikir lain yang menenteramkan hati."
    ),
}
