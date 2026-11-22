# Safety MVP

`SafetyGuardrails` berjalan sebelum embedding dan LLM. Pattern krisis deterministik menghasilkan
respons tetap dan kontak `CRISIS_LINE`; pesan krisis tidak pernah dikirim ke model, embedding, atau
database retrieval.

Pesan nonkrisis boleh masuk retrieval. Jika skor vector rendah, source kosong, provider gagal,
atau jawaban tidak lolos citation/quality gate, sistem menampilkan fallback jujur dan tidak
mengarang ayat.

Model berjalan lokal. Model 3b di CPU lebih sering gagal quality gate; kegagalan tersebut
menghasilkan sources-only response, bukan jawaban tanpa sitasi.

Qalbu bukan diagnosis, terapi, layanan krisis, atau fatwa. Verifikasi kontak bantuan sebelum
deployment publik.
