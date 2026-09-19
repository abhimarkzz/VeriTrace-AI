# VeriTrace AI — Dataset Card

## Datasets

### 1. X-Fact
| Field | Value |
|-------|-------|
| **Source** | [utahnlp/x-fact](https://huggingface.co/datasets/utahnlp/x-fact) (HuggingFace) |
| **Paper** | ACL 2021 — "X-FACT: A New Benchmark Dataset for Multilingual Fact Checking" |
| **License** | Research use |
| **Languages** | 25 (ar, bg, de, en, es, fa, fr, ge, hi, hu, id, it, ja, ka, ko, nl, no, pl, pt, ro, ru, sq, sr, ta, tr) |
| **Labels** | `true`, `mostly_true`, `half_true`, `mostly_false`, `false`, `unverifiable`, `other` |
| **Size** | ~31,189 claims (actual count reported by validate.py after download) |

### 2. FEVER
| Field | Value |
|-------|-------|
| **Source** | [fever/fever](https://huggingface.co/datasets/fever/fever) v1.0 (HuggingFace) |
| **Paper** | NAACL 2018 — "FEVER: a Large-scale Dataset for Fact Extraction and VERification" |
| **License** | CC BY-SA 3.0 |
| **Languages** | English only |
| **Labels** | `SUPPORTS`, `REFUTES`, `NOT ENOUGH INFO` |
| **Size** | ~185,445 claims (actual count reported by validate.py after download) |

### 3. AVeriTeC
| Field | Value |
|-------|-------|
| **Source** | [chenxwh/AVeriTeC](https://huggingface.co/chenxwh/AVeriTeC) (HuggingFace model repo) |
| **Paper** | NeurIPS 2024 — "AVeriTeC: A Dataset for Real-world Claim Verification" |
| **License** | CC BY-SA 4.0 |
| **Languages** | English only |
| **Labels** | `Supported`, `Refuted`, `Not Enough Evidence`, `Conflicting Evidence/Cherry-picking` |
| **Size** | Actual count reported by validate.py after download |

---

## Common Schema

Every record is normalized to:

```json
{
  "id": "{dataset}_{original_id}",
  "claim": "The factual claim text",
  "label": "original_dataset_label",
  "mapped_label": "VERITRACE_CANONICAL_LABEL",
  "language": "en",
  "evidence": [{"title": "...", "snippet": "...", "url": "..."}],
  "source": "original source attribution",
  "dataset": "fever"
}
```

---

## Label Mappings

Original labels are **always preserved** in the `label` field. The `mapped_label` field contains the VeriTrace canonical label. Mappings are **explicit and documented** — never silent.

### FEVER → VeriTrace
| Original | Mapped |
|----------|--------|
| `SUPPORTS` | `SUPPORTED` |
| `REFUTES` | `POTENTIALLY_MISLEADING` |
| `NOT ENOUGH INFO` | `INSUFFICIENT_EVIDENCE` |

### X-Fact → VeriTrace
| Original | Mapped |
|----------|--------|
| `true` | `SUPPORTED` |
| `mostly_true` | `SUPPORTED` |
| `half_true` | `CONFLICTING_EVIDENCE` |
| `mostly_false` | `POTENTIALLY_MISLEADING` |
| `false` | `POTENTIALLY_MISLEADING` |
| `unverifiable` | `INSUFFICIENT_EVIDENCE` |
| `other` | `INSUFFICIENT_EVIDENCE` |

### AVeriTeC → VeriTrace
| Original | Mapped |
|----------|--------|
| `Supported` | `SUPPORTED` |
| `Refuted` | `POTENTIALLY_MISLEADING` |
| `Not Enough Evidence` | `INSUFFICIENT_EVIDENCE` |
| `Conflicting Evidence/Cherry-picking` | `CONFLICTING_EVIDENCE` |

---

## Preprocessing

1. **Download**: Raw JSONL files saved to `data/raw/{dataset}/`
2. **Normalize**: Apply label mappings, extract common fields → `data/processed/normalized_{dataset}.jsonl`
3. **Deduplicate**: Remove exact duplicates (by claim text MD5 hash)
4. **Split**: Stratified by `(mapped_label, language)` → 70/15/15 train/val/test
5. **Language subsets**: Per-language eval files for en, hi, te

---

## Split Method

- **Stratification**: By `mapped_label` × `language` to maintain class and language balance
- **Seed**: 42 (deterministic, reproducible)
- **Ratios**: 70% train / 15% validation / 15% test
- **Leakage check**: Zero claim text overlap verified between all split pairs
- **Deduplication**: Before splitting, exact duplicates removed

---

## Known Limitations

1. **X-Fact Hindi data**: Available but limited in quantity
2. **Telugu data**: X-Fact may contain Telugu-related claims, but coverage is sparse. No dedicated Telugu fact-checking dataset exists in the public domain
3. **FEVER**: English-only, Wikipedia-grounded — may not generalize to social media claims
4. **AVeriTeC**: English-only, relatively small compared to FEVER
5. **Label granularity loss**: X-Fact's 7-level scale is compressed to 4 VeriTrace labels. Original labels preserved for fine-grained analysis
6. **Evidence quality**: FEVER evidence is Wikipedia sentence IDs; AVeriTeC has web-scraped QA pairs; X-Fact has minimal evidence
7. **Dataset sizes**: All sizes in this card are documented from the dataset papers. Actual counts after download are reported by `validate.py` — never fabricated
