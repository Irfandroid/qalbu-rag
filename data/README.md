# Data sources

Source corpora are intentionally not committed. They retain separate provenance,
attribution, and licensing requirements.

## Quran.com snapshot

Generate the Arabic Uthmani + attributed Saheeh International snapshot:

```bash
python scripts/fetch_quran_com.py
```

Expected output:

```text
data/external/quran-com/saheeh-international.json
```

The script verifies all 6,236 ayahs before saving the snapshot.

## Community Arabic tafsir

Download the community dataset from Kaggle:

```bash
curl -L -o data/external/quran-tafseer/quranic-ayahs-with-tafseer-json-dataset.zip \
  https://www.kaggle.com/api/v1/datasets/download/abdelrahmanahmed110/quranic-ayahs-with-tafseer-json-dataset
```

Extract its JSON files into:

```text
data/external/quran-tafseer/raw/
```

Current local corpus contains 103 of 114 surahs. Qalbu labels this source as
an unverified community dataset, never as Kemenag or an official tafsir.

## Temporary sample

`data/temporary/` is a small development sample. It is not an official Quran
source and must not be presented as one.
