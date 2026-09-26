# Safety MVP

`SafetyGuardrails` berjalan sebelum embedding dan LLM. Pattern krisis deterministik menghasilkan
respons tetap dan kontak `CRISIS_LINE`; pesan krisis tidak pernah dikirim ke Gemini.

Pesan nonkrisis boleh masuk retrieval. Jika skor vector rendah, source kosong, provider gagal,
atau jawaban tidak lolos citation/quality gate, sistem menampilkan fallback jujur dan tidak
mengarang ayat.

Qalbu bukan diagnosis, terapi, layanan krisis, atau fatwa. Verifikasi kontak bantuan sebelum
deployment publik.
