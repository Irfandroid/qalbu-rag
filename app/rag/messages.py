"""User-facing copy for non-generated Qalbu responses.

Keeping this text in one module makes the product language reviewable without
reading orchestration code. Generated reflections never come from here.
"""

# Safety
IMMEDIATE_DANGER_FALLBACK = "Jika ada bahaya segera, hubungi layanan darurat setempat."
IMMEDIATE_DANGER_SAFETY_NOTE = "Dukungan segera disarankan."
HUMAN_SUPPORT_NOTE = (
    "Jika keadaan terasa makin berat, hubungi orang tepercaya atau tenaga "
    "kesehatan mental yang dapat mendampingi secara langsung."
)

# Retrieval fallbacks
NO_RELEVANT_CONTEXT = (
    "Aku belum menemukan ayat yang cukup relevan. "
    "Coba ceritakan kembali dengan kata yang lebih spesifik."
)

# The chat endpoint and the SSE endpoint intentionally expose different copy
# lengths: the SSE bubble is compact, the JSON endpoint has room for context.
TRANSLATION_UNAVAILABLE = (
    "Terjemahan Indonesia terverifikasi belum tersedia pada sumber aktif. "
    "Teks Arab dan tafsir sumber tetap ditampilkan tanpa dibuatkan terjemahan "
    "atau refleksi oleh model."
)
TRANSLATION_UNAVAILABLE_NOTE = (
    "Dataset aktif adalah sumber komunitas, bukan sumber resmi Kemenag."
)
TRANSLATION_UNAVAILABLE_BRIEF = (
    "Terjemahan Indonesia terverifikasi belum tersedia. "
    "Qalbu tidak akan menerjemahkan atau membuat refleksi dari model."
)

SOURCES_ONLY = (
    "Refleksi AI sedang tidak tersedia saat ini. Sumber Al-Qur'an hasil pencarian "
    "tetap ditampilkan agar kamu dapat membacanya dan menilainya sendiri dengan tenang."
)

# Scope routing
SCOPE_LIMIT = (
    "Qalbu saat ini berfokus pada ruang refleksi dan informasi berbasis sumber "
    "Al-Qur'an. Untuk pertanyaan praktis atau umum, gunakan sumber yang "
    "sesuai; Qalbu dapat membantu bila kamu ingin membahas sisi reflektifnya."
)
OUT_OF_SCOPE = (
    "Pertanyaan itu berada di luar ruang refleksi Qalbu. "
    "Ceritakan perasaan atau keadaan yang sedang kamu hadapi agar Qalbu "
    "dapat mencari sumber Al-Qur'an yang relevan."
)
NEEDS_CLARIFICATION = (
    "Bisa ceritakan sedikit lebih spesifik tentang hal yang ingin kamu pahami? "
    "Qalbu dapat membantu refleksi dan mencari sumber Al-Qur'an yang relevan."
)
