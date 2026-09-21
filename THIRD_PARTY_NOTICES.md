# Third-party data notices

Qalbu's source code repository intentionally excludes downloaded Quran and tafsir corpora. Users who fetch external data are responsible for reviewing the current provider terms, attribution requirements, and redistribution permissions.

## Quran.com snapshot

- Provider: [Quran.com](https://quran.com/)
- API used by `scripts/fetch_quran_com.py`: `https://api.quran.com/api/v4`
- Arabic field: Uthmani text returned by the provider
- English translation: Saheeh International, resource ID `20`
- Local output: `data/external/quran-com/saheeh-international.json` (Git-ignored)

The repository does not assert that the English translation is public domain or redistributable under the code's future license. Verify Quran.com/Quran Foundation terms and the translation owner's requirements before bundling or redistributing a snapshot.

## Community Quran tafsir dataset

- Kaggle dataset: [Quranic Ayahs with Tafseer JSON Dataset](https://www.kaggle.com/datasets/abdelrahmanahmed110/quranic-ayahs-with-tafseer-json-dataset)
- Dataset author shown by Kaggle metadata: Abdelrahman Ahmed Eldaba
- Kaggle metadata claim: `CC0: Public Domain`
- Upstream verse source named by the dataset: [EveryAyah](https://everyayah.com/)
- Upstream tafsir source named by the dataset: [SurahQuran](https://surahquran.com/tafseer-alquran.html)
- Local output/archive: `data/external/quran-tafseer/` (raw JSON and ZIP are Git-ignored)

The Kaggle label has not been independently verified against every upstream source's rights. Treat the corpus as an unverified community source, preserve provenance, and confirm upstream permissions before public redistribution.

## Model and service dependencies

Model weights, Python packages, Ollama, Supabase, and other services remain under their own licenses and terms. Their inclusion in setup instructions does not relicense them.

## Not Kemenag

Neither current corpus is an official Kementerian Agama Republik Indonesia dataset. Qalbu must not label English translation, model paraphrase, or community tafsir as an official Kemenag translation or tafsir.
